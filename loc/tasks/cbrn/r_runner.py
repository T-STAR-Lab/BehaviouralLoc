"""cbrn/r runner — Nuclear tasks r1, r2, r3 (merged).

  r1: Nuclear open-ended questions (150 items) — answers saved for judge
  r2: Nuclear MCQ (100 questions, self-scoring)
  r3: Nuclear SMR open-ended questions (50 items) — answers saved for judge

Usage (from repo root):
    python loc/tasks/cbrn/r/runner.py --model qwen3-14b --tasks r1 r2 r3
    python loc/tasks/cbrn/r/runner.py --model qwen3-14b --tasks r2 --target-runs 3
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List

from tqdm import tqdm

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from loc.chat import call_model
from loc.tasks.cbrn.prompts import R_OPEN_PROMPT, R2_MCQ_PROMPT
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
from loc.utils.text import strip_thinking

DEFAULT_OUTPUT_DIR = Path("./results/cbrn")


# ---------------------------------------------------------------------------
# Answer extractor (r2 only — r1/r3 save raw text)
# ---------------------------------------------------------------------------

def _extract_r2(raw: str) -> str:
    text = strip_thinking(raw).strip()
    matches = re.findall(r'\b([A-E])\b', text)
    return matches[-1] if matches else ""


# ---------------------------------------------------------------------------
# Task evaluators
# ---------------------------------------------------------------------------

def evaluate_r1(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/r1.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []

    for item in tqdm(data, desc="[r1]"):
        prompt = R_OPEN_PROMPT.format(question=item["Question"])
        raw = call_model(model_name, [{"role": "user", "content": prompt}]) or ""
        answer = strip_thinking(raw).strip()

        keys = item.get("keys", [])
        results.append({
            "Question": item["Question"],
            "Model_Answer": answer,
            "Reference_Answer": item.get("Answer", ""),
            "Reference_Keys": keys,
            "S": len(keys),
        })

    atomic_write_json(run_path, results)
    print(f"[r1 DONE] {len(results)} answers saved -> {run_path}")


def evaluate_r2(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/r2.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []
    correct = 0

    for item in tqdm(data, desc="[r2]"):
        choices_text = "\n".join(item["choice"])
        prompt = R2_MCQ_PROMPT.format(question=item["Q"], choices=choices_text)
        raw = call_model(model_name, [{"role": "user", "content": prompt}]) or ""
        response = _extract_r2(raw)
        is_correct = response == item["truth"]
        if is_correct:
            correct += 1

        results.append({
            "id": item["id"],
            "question": item["Q"],
            "choices": item["choice"],
            "answer": item["truth"],
            "response": response,
            "correct": is_correct,
        })

    total = len(results)
    accuracy = correct / total if total else 0.0
    atomic_write_json(run_path, {"accuracy": accuracy, "n_correct": correct, "n_total": total, "items": results})
    print(f"[r2 DONE] correct={correct}/{total} accuracy={accuracy:.2%}")


def evaluate_r3(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/r3.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []

    for item in tqdm(data, desc="[r3]"):
        prompt = R_OPEN_PROMPT.format(question=item["Question"])
        raw = call_model(model_name, [{"role": "user", "content": prompt}]) or ""
        answer = strip_thinking(raw).strip()

        keys = item.get("keys", [])
        results.append({
            "Question": item["Question"],
            "Model_Answer": answer,
            "Reference_Answer": item.get("Answer", ""),
            "Reference_Keys": keys,
            "S": len(keys),
        })

    atomic_write_json(run_path, results)
    print(f"[r3 DONE] {len(results)} answers saved -> {run_path}")


# ---------------------------------------------------------------------------
# Run-loop dispatcher
# ---------------------------------------------------------------------------

_EVALUATORS = {
    "r1": evaluate_r1,
    "r2": evaluate_r2,
    "r3": evaluate_r3,
}


def _run_task(task: str, model: str, outdir: Path, target_runs: int) -> None:
    run_dir = outdir / model / task
    existing = existing_run_indices(run_dir)
    while completed_run_count(existing, target_runs) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        run_path = run_dir / f"run_{idx:03d}.json"
        print(f"[{task}] run={idx:03d}/{target_runs}")
        _EVALUATORS[task](model, run_path)
        existing = existing_run_indices(run_dir)
    print(f"[{task}] logs -> {run_dir.resolve()}")


def main():
    p = argparse.ArgumentParser(description="cbrn/r — Nuclear tasks r1/r2/r3")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--tasks", nargs="+", choices=["r1", "r2", "r3"], default=["r1", "r2", "r3"])
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    args = p.parse_args()

    outdir = Path(args.outdir)
    for task in args.tasks:
        _run_task(task, args.model, outdir, args.target_runs)


if __name__ == "__main__":
    main()
