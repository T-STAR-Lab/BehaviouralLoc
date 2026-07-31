"""CBRN nuclear runner for canonical CB task components.

  cb1_nuclear: Nuclear open-ended questions (150 items) — answers saved for judge
  cb2_nuclear: Nuclear MCQ (100 questions, self-scoring)
  cb3_nuclear: Nuclear SMR open-ended questions (50 items) — answers saved for judge

Usage (from repo root):
    python loc/tasks/cbrn/r_runner.py --model qwen3-14b --tasks cb1_nuclear cb2_nuclear cb3_nuclear
    python loc/tasks/cbrn/r_runner.py --model qwen3-14b --tasks cb2_nuclear --target-runs 3
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
# Answer extractor (CB.2 nuclear only; CB.1/CB.3 nuclear save raw text)
# ---------------------------------------------------------------------------

def _extract_r2(raw: str) -> str:
    text = strip_thinking(raw).strip()
    matches = re.findall(r'\b([A-E])\b', text)
    return matches[-1] if matches else ""


# ---------------------------------------------------------------------------
# Task evaluators
# ---------------------------------------------------------------------------

def evaluate_cb1_nuclear(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/cb1_nuclear.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []

    for item in tqdm(data, desc="[cb1_nuclear]"):
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
    print(f"[cb1_nuclear DONE] {len(results)} answers saved -> {run_path}")


def evaluate_cb2_nuclear(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/cb2_nuclear.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []
    correct = 0

    for item in tqdm(data, desc="[cb2_nuclear]"):
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
    print(f"[cb2_nuclear DONE] correct={correct}/{total} accuracy={accuracy:.2%}")


def evaluate_cb3_nuclear(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/cb3_nuclear.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []

    for item in tqdm(data, desc="[cb3_nuclear]"):
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
    print(f"[cb3_nuclear DONE] {len(results)} answers saved -> {run_path}")


# ---------------------------------------------------------------------------
# Run-loop dispatcher
# ---------------------------------------------------------------------------

_EVALUATORS = {
    "cb1_nuclear": evaluate_cb1_nuclear,
    "cb2_nuclear": evaluate_cb2_nuclear,
    "cb3_nuclear": evaluate_cb3_nuclear,
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
    p = argparse.ArgumentParser(description="CBRN nuclear canonical components")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--tasks", nargs="+", choices=list(_EVALUATORS), default=list(_EVALUATORS))
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    args = p.parse_args()

    outdir = Path(args.outdir)
    for task in args.tasks:
        _run_task(task, args.model, outdir, args.target_runs)


if __name__ == "__main__":
    main()
