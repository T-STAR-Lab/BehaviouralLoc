"""sabotage — run the agent + supervisor pipeline through inspect_ai + docker sandbox (serial)."""

import argparse
import json
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional

from tqdm import tqdm

# ---- shared modules ----
import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))
from loc.tasks.sabotage.model_config import get_inspect_model_spec
from loc.tasks.sabotage.workflow_solver import multi_stage_solver
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
from loc.utils.parsing import extract_json_from_text, safe_id
# ------------------------

from inspect_ai import Task, eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import includes


DEFAULT_TASKS_PATH = Path("./data/sabotage/task2.json")
DEFAULT_OUTPUT_DIR = Path("./results/sabotage")
DEFAULT_COMPOSE = Path("./docker/sabotage/compose.yaml")


def _evaluate_one(
    entry: Dict[str, Any],
    inspect_model: str,
    eval_kwargs: dict,
    model_args: dict,
    compose_path: str,
    entry_log_dir: Path,
    time_limit: int,
    max_retries: int,
) -> Dict[str, Any]:
    risk_task = entry.get("risk_task", "")
    ability = entry.get("ability", "")

    # The actual agent prompt is built inside ``multi_stage_solver`` (it needs
    # to reference ``/data`` — the docker mount point from docker/sabotage/Dockerfile).
    # We only seed Sample.input with a placeholder; ``solve()`` overwrites
    # state.messages before stage 1 runs.
    entry_log_dir.mkdir(parents=True, exist_ok=True)
    samples = [Sample(
        id=entry["id"],
        input="",
        metadata={"risk_task": risk_task, "ability": ability},
    )]

    last_error: Optional[Exception] = None
    record: Optional[Dict[str, Any]] = None

    for attempt in range(1, max_retries + 1):
        try:
            task = Task(
                dataset=MemoryDataset(samples),
                solver=multi_stage_solver(),
                scorer=includes(),
                sandbox=("docker", compose_path),
            )
            results = eval(
                task,
                model=inspect_model,
                model_args=model_args,
                log_buffer=1,
                log_format="json",
                log_dir=str(entry_log_dir),
                time_limit=time_limit,
                **eval_kwargs,
            )
            for r in results:
                sample = r.samples[0]
                raw_output = sample.output.completion
                try:
                    eval_json = extract_json_from_text(raw_output)
                except ValueError as ve:
                    print(f"[WARN] JSON parse error for sample {sample.id}: {ve}")
                    eval_json = {"task_completed": False, "dangerous_actions": False, "refused": False}

                record = {
                    "id": sample.id,
                    "risk_task": sample.metadata.get("risk_task"),
                    "ability": sample.metadata.get("ability"),
                    "agent_output": sample.metadata.get("stage1_output"),
                    "supervisor_output": raw_output,
                    "task_completed": bool(eval_json.get("task_completed", False)),
                    "dangerous_actions": bool(eval_json.get("dangerous_actions", False)),
                    "refused": bool(eval_json.get("refused", False)),
                }
            break
        except Exception as e:
            last_error = e
            msg = str(e)
            retriable = any(s in msg for s in [
                "TLS handshake timeout",
                "Failed to build docker containers",
                "failed to solve",
                "failed to resolve source metadata",
                "INVALID REQUEST",
            ])
            if retriable and attempt < max_retries:
                print(f"[attempt {attempt}/{max_retries}] retriable docker/TLS error: {e}")
                sleep(5)
                continue
            print(f"[ERROR] entry {entry.get('id')} attempt {attempt} failed: {e}")
            break

    if record is None:
        print(f"[WARN] giving up on entry id={entry.get('id')} (last_error={last_error})")
        record = {
            "id": entry.get("id"),
            "risk_task": risk_task,
            "ability": ability,
            "agent_output": None,
            "supervisor_output": None,
            "task_completed": False,
            "dangerous_actions": False,
            "refused": False,
        }
    return record


def parse_args():
    p = argparse.ArgumentParser(description="sabotage — inspect_ai + docker eval (serial)")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--tasks-path", default=str(DEFAULT_TASKS_PATH))
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--compose-file", default=str(DEFAULT_COMPOSE))
    p.add_argument("--max-retries", type=int, default=5)
    p.add_argument("--time-limit", type=int, default=1200)
    p.add_argument("--target-runs", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    task_name = Path(args.tasks_path).stem

    inspect_model, eval_kwargs, model_args = get_inspect_model_spec(args.model, max_tokens=args.max_tokens)
    print(f"[INFO] inspect model: {inspect_model}")
    print(f"[INFO] eval kwargs: {eval_kwargs}")
    print(f"[INFO] model args: {model_args}")

    with open(args.tasks_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    run_dir = out_dir / args.model / task_name
    existing = existing_run_indices(run_dir)

    while completed_run_count(existing, args.target_runs) < args.target_runs:
        run_index = next_missing_run_index(existing, args.target_runs)
        run_path = run_dir / f"run_{run_index:03d}.json"
        inspect_log_dir = Path("./logs/sabotage") / args.model / task_name / f"run_{run_index:03d}"
        inspect_log_dir.mkdir(parents=True, exist_ok=True)

        print(f"[sabotage] task={task_name} run={run_index:03d}/{args.target_runs}")

        records: List[Optional[Dict[str, Any]]] = [None] * len(raw_data)
        for idx, entry in enumerate(tqdm(raw_data, desc=f"[sabotage] {task_name} run {run_index:03d}")):
            entry_log_dir = inspect_log_dir / safe_id(entry.get("id"))
            records[idx] = _evaluate_one(
                entry,
                inspect_model=inspect_model,
                eval_kwargs=eval_kwargs,
                model_args=model_args,
                compose_path=args.compose_file,
                entry_log_dir=entry_log_dir,
                time_limit=args.time_limit,
                max_retries=args.max_retries,
            )

        atomic_write_json(run_path, records)
        print(f"[sabotage DONE] per-sample -> {run_path.resolve()}")
        print(f"[sabotage DONE] inspect logs -> {inspect_log_dir.resolve()}")
        existing = existing_run_indices(run_dir)


if __name__ == "__main__":
    main()
