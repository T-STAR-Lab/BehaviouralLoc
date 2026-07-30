# runner.py - shared evaluation driver for all demos.
#
# Each demo's task.py supplies a solver factory, prompt module, sample id, and
# a record-building callback. This file handles CLI parsing, retries, JSON
# extraction, and writing results in a consistent layout:
#
#   results/<dim>/<demo>/<model>/variant_<N>/eval_results_<ts>.json
#   results/<dim>/<demo>/<model>/variant_<N>/trajectory_<ts>.txt
#   <demo>/logs/<model>/...                                  (inspect_ai native)

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import re
import sys
from datetime import datetime
from time import sleep
from typing import Any, Callable, Dict, Optional

from inspect_ai import Task, eval as inspect_eval
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import includes

from model_config import get_inspect_model_spec

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #
def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Best-effort: pull the first balanced JSON object out of an LLM response."""
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape_next = False
        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj.get("reasoning"), list):
                            obj["reasoning"] = "\n".join(str(x) for x in obj["reasoning"])
                        return obj
                    except Exception:
                        break
        start = text.find("{", start + 1)

    safe_match = re.search(r'"safe"\s*:\s*(true|false)', text, re.IGNORECASE)
    if safe_match:
        reasoning_val = "parse_error_recovered"
        m = re.search(r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)', text)
        if m:
            reasoning_val = m.group(1)
        return {"safe": safe_match.group(1).lower() == "true", "reasoning": reasoning_val}

    raise ValueError("No JSON object found in model output.")


# --------------------------------------------------------------------------- #
# Variant loader
# --------------------------------------------------------------------------- #
def load_variant(demo_dir: pathlib.Path, variant_num: int, prompts_module) -> None:
    """Load variants/variant_N.py and inject AGENT_SYSTEM_PROMPT_N into the demo's prompts module."""
    variant_file = demo_dir / "variants" / f"variant_{variant_num}.py"
    spec = importlib.util.spec_from_file_location(f"variant_{variant_num}", variant_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    prompt_text = getattr(mod, f"AGENT_SYSTEM_PROMPT_{variant_num}")
    setattr(prompts_module, "AGENT_SYSTEM_PROMPT", prompt_text)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_arg_parser(description: str = "Run an evaluation demo.") -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--model-name", required=True, help="Model key in MODEL_REGISTRY")
    p.add_argument("--variant", type=int, required=True, help="Variant number (1-20)")
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--max-retries", type=int, default=5)
    p.add_argument("--time-limit", type=int, default=600, help="inspect eval time_limit (s)")
    return p


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #
def run_evaluation(
    *,
    demo_id: str,                                # e.g. "Self-Improvement/demo1"
    sample_id: str,                              # e.g. "data_collection_1"
    sample_input: str,                           # the AGENT_*_PROMPT text
    solver_factory: Callable[..., Any],          # called with trajectory_path=<str>
    record_builder: Callable[[Any, Optional[int]], Dict[str, Any]],
    failure_record: Dict[str, Any],              # used when all retries fail (id/variant are injected)
    prompts_module=None,                         # demo's prompts module (for variant injection)
    demo_dir: Optional[pathlib.Path] = None,     # demo directory (for variants/ and inspect logs/)
    extra_args: Optional[argparse.ArgumentParser] = None,
) -> pathlib.Path:
    """Run one (demo, model, variant) evaluation. Returns the eval_results path."""
    parser = extra_args or build_arg_parser(f"Run {demo_id}")
    args = parser.parse_args()

    if demo_dir is None:
        # Best-effort: assume caller is at <repo>/<dim>/<demo>/task.py
        import inspect
        caller = pathlib.Path(inspect.stack()[1].filename).resolve()
        demo_dir = caller.parent

    if args.variant is not None and prompts_module is not None:
        load_variant(demo_dir, args.variant, prompts_module)

    # ---- resolve inspect_ai model spec ----
    inspect_model, eval_kwargs, model_args = get_inspect_model_spec(
        args.model_name, max_tokens=args.max_tokens
    )
    print(f"[INFO] demo: {demo_id}  model: {args.model_name}  variant: {args.variant}")

    # ---- paths ----
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    variant_tag = f"variant_{args.variant}" if args.variant is not None else "no_variant"
    # sanitize ":" (e.g. "vllm:Qwen3.5-27B") for filesystem-safe dir names
    model_dir_name = args.model_name.replace(":", "_")

    # our outputs: centralized at repo root
    out_dir = REPO_ROOT / "results" / demo_id / model_dir_name / variant_tag
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / f"eval_results_{ts}.json"
    trajectory_path = out_dir / f"trajectory_{ts}.txt"

    # inspect_ai native logs: stay in the demo dir
    inspect_log_dir = demo_dir / "logs" / model_dir_name
    inspect_log_dir.mkdir(parents=True, exist_ok=True)

    # ---- sample ----
    samples = [Sample(id=sample_id, input=sample_input, metadata={})]
    dataset = MemoryDataset(samples)

    # ---- retry loop ----
    record: Optional[Dict[str, Any]] = None
    last_error: Optional[BaseException] = None
    for attempt in range(1, args.max_retries + 1):
        try:
            task = Task(
                dataset=dataset,
                solver=solver_factory(trajectory_path=str(trajectory_path)),
                scorer=includes(),
                sandbox="docker",
            )
            results = inspect_eval(
                task,
                model=inspect_model,
                model_args=model_args,
                log_buffer=1,
                log_format="json",
                log_dir=str(inspect_log_dir),
                time_limit=args.time_limit,
                **eval_kwargs,
            )
            sample = results[0].samples[0]
            if sample.error:
                raise RuntimeError(f"Sample execution failed: {sample.error}")

            record = record_builder(sample, args.variant)
            break
        except Exception as e:
            last_error = e
            print(f"[Attempt {attempt}/{args.max_retries}] Error: {e}")
            if attempt < args.max_retries:
                sleep(5)

    if record is None:
        print(f"[WARN] Evaluation failed (last_error={last_error})")
        record = {"id": sample_id, "variant": args.variant, **failure_record}

    record.setdefault("id", sample_id)
    record.setdefault("variant", args.variant)

    results_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[DONE] Results    -> {results_path}")
    if trajectory_path.exists():
        print(f"[DONE] Trajectory -> {trajectory_path}")
    print(f"[DONE] Inspect    -> {inspect_log_dir}")
    return results_path
