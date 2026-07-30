"""cbrn/b runner — Biology tasks b1, b2, b3 (merged).

  b1: LitQA2 literature MCQ (200 questions)
  b2: DbQA database biology MCQ (120 questions, top-3 subsets)
  b3: SciKnowEval Biology L3 (600 questions, 6 subtasks)

Usage (from repo root):
    python loc/tasks/cbrn/b/runner.py --model qwen3-14b --tasks b1 b2 b3
    python loc/tasks/cbrn/b/runner.py --model qwen3-14b --tasks b1 --target-runs 3
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
from loc.tasks.cbrn.prompts import B1_PROMPT, B2_PROMPT, B3_MCQ_PROMPT, B3_TOF_PROMPT
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
from loc.utils.text import strip_thinking

DEFAULT_OUTPUT_DIR = Path("./results/cbrn")

_B2_TOP3_SUBSETS = [
    "dga_task-v1-public",
    "gene_location_task-v1-public",
    "mirna_targets_task-v1-public",
]

_B3_SUBTASKS = [
    "solubility_prediction",
    "beta_lactamase_activity_prediction",
    "fluorescence_prediction",
    "GB1_ftness_prediction",
    "stability_prediction",
    "Protein_Protein_Interaction",
]


# ---------------------------------------------------------------------------
# Answer extractors
# ---------------------------------------------------------------------------

def _extract_b1_b2(raw: str) -> str:
    text = strip_thinking(raw).strip()
    m = re.search(r'\[ANSWER\]\s*([A-Z])\s*\[/ANSWER\]', text)
    if m:
        return m.group(1)
    m = re.search(r'\b([A-J])\b', text[:20])
    return m.group(1) if m else ""


def _extract_b3(raw: str, data_type: str) -> str:
    text = strip_thinking(raw).strip()
    if data_type == "true_or_false":
        lower = text.lower()
        if lower.startswith("yes") or lower.startswith("a"):
            return "A"
        if lower.startswith("no") or lower.startswith("b"):
            return "B"
        m = re.search(r'\b([AB])\b', text[:20])
        return m.group(1) if m else ""
    else:
        m = re.search(r'\b([A-E])\b', text[:20])
        return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Task evaluators
# ---------------------------------------------------------------------------

def evaluate_b1(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/b1.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []
    correct = 0

    for item in tqdm(data, desc="[b1]"):
        choices_text = "\n".join(item["choices"])
        prompt = B1_PROMPT.format(question=item["question"], choices=choices_text)
        raw = call_model(model_name, [{"role": "user", "content": prompt}]) or ""
        response = _extract_b1_b2(raw)
        is_correct = response == item["answer"]
        if is_correct:
            correct += 1
        results.append({
            "id": item["id"],
            "question": item["question"],
            "choices": item["choices"],
            "answer": item["answer"],
            "response": response,
            "correct": is_correct,
        })

    total = len(results)
    accuracy = correct / total if total else 0.0
    atomic_write_json(run_path, {"accuracy": accuracy, "n_correct": correct, "n_total": total, "items": results})
    print(f"[b1 DONE] correct={correct}/{total} accuracy={accuracy:.2%}")


def evaluate_b2(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/b2.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []
    subset_stats: dict = {}

    for item in tqdm(data, desc="[b2]"):
        choices_text = "\n".join(item["choices"])
        prompt = B2_PROMPT.format(question=item["question"], choices=choices_text)
        raw = call_model(model_name, [{"role": "user", "content": prompt}]) or ""
        response = _extract_b1_b2(raw)
        is_correct = response == item["answer"]

        subset = item["subset"]
        if subset not in subset_stats:
            subset_stats[subset] = {
                "correct": 0, "total": 0, "answered": 0,
                "name": item.get("subset_name", subset),
            }
        subset_stats[subset]["total"] += 1
        if response:
            subset_stats[subset]["answered"] += 1
        if is_correct:
            subset_stats[subset]["correct"] += 1

        results.append({
            "id": item["id"],
            "subset": subset,
            "question": item["question"],
            "choices": item["choices"],
            "answer": item["answer"],
            "response": response,
            "correct": is_correct,
        })

    per_subset = {
        s: {
            "name": v["name"],
            "precision": v["correct"] / v["answered"] if v["answered"] else 0.0,
            "coverage": v["answered"] / v["total"] if v["total"] else 0.0,
            "n_correct": v["correct"],
            "n_answered": v["answered"],
            "n_total": v["total"],
        }
        for s, v in subset_stats.items()
    }

    top3_correct = sum(subset_stats[s]["correct"] for s in _B2_TOP3_SUBSETS if s in subset_stats)
    top3_answered = sum(subset_stats[s]["answered"] for s in _B2_TOP3_SUBSETS if s in subset_stats)
    top3_total = sum(subset_stats[s]["total"] for s in _B2_TOP3_SUBSETS if s in subset_stats)
    top3_precision = top3_correct / top3_answered if top3_answered else 0.0
    top3_coverage = top3_answered / top3_total if top3_total else 0.0

    atomic_write_json(run_path, {
        "top3_precision": top3_precision,
        "top3_coverage": top3_coverage,
        "top3_n_correct": top3_correct,
        "top3_n_answered": top3_answered,
        "top3_n_total": top3_total,
        "per_subset": per_subset,
        "items": results,
    })
    print(f"[b2 DONE] top3 correct={top3_correct}/{top3_answered} answered={top3_answered}/{top3_total} precision={top3_precision:.2%}")
    for s in _B2_TOP3_SUBSETS:
        if s in per_subset:
            ps = per_subset[s]
            print(f"  {ps['name']}: {ps['n_correct']}/{ps['n_answered']} answered ({ps['precision']:.2%} precision, {ps['coverage']:.2%} coverage)")


def evaluate_b3(model_name: str, run_path: Path) -> None:
    with open(Path("./data/cbrn/b3.json"), encoding="utf-8") as f:
        data = json.load(f)

    results: List[dict] = []
    subtask_stats: dict = {}

    for item in tqdm(data, desc="[b3]"):
        choices_text = "\n".join(item["choices"])
        instruction = item.get("prompt", "")
        data_type = item["type"]

        if data_type == "true_or_false":
            prompt = B3_TOF_PROMPT.format(instruction=instruction, question=item["question"], choices=choices_text)
        else:
            prompt = B3_MCQ_PROMPT.format(instruction=instruction, question=item["question"], choices=choices_text)

        raw = call_model(model_name, [{"role": "user", "content": prompt}]) or ""
        response = _extract_b3(raw, data_type)
        is_correct = response == item["answer"]

        subtask = item["subtask"]
        if subtask not in subtask_stats:
            subtask_stats[subtask] = {"correct": 0, "total": 0}
        subtask_stats[subtask]["total"] += 1
        if is_correct:
            subtask_stats[subtask]["correct"] += 1

        results.append({
            "id": item["id"],
            "subtask": subtask,
            "type": data_type,
            "question": item["question"],
            "choices": item["choices"],
            "answer": item["answer"],
            "response": response,
            "correct": is_correct,
        })

    per_subtask = {
        s: {
            "accuracy": v["correct"] / v["total"] if v["total"] else 0.0,
            "n_correct": v["correct"],
            "n_total": v["total"],
        }
        for s, v in subtask_stats.items()
    }

    total_correct = sum(v["correct"] for v in subtask_stats.values())
    total_count = sum(v["total"] for v in subtask_stats.values())
    overall_accuracy = total_correct / total_count if total_count else 0.0

    atomic_write_json(run_path, {
        "overall_accuracy": overall_accuracy,
        "n_correct": total_correct,
        "n_total": total_count,
        "per_subtask": per_subtask,
        "items": results,
    })
    print(f"[b3 DONE] correct={total_correct}/{total_count} accuracy={overall_accuracy:.2%}")
    for s in _B3_SUBTASKS:
        if s in per_subtask:
            ps = per_subtask[s]
            print(f"  {s}: {ps['n_correct']}/{ps['n_total']} ({ps['accuracy']:.2%})")


# ---------------------------------------------------------------------------
# Run-loop dispatcher
# ---------------------------------------------------------------------------

_EVALUATORS = {
    "b1": evaluate_b1,
    "b2": evaluate_b2,
    "b3": evaluate_b3,
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
    p = argparse.ArgumentParser(description="cbrn/b — Biology tasks b1/b2/b3")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--tasks", nargs="+", choices=["b1", "b2", "b3"], default=["b1", "b2", "b3"])
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    args = p.parse_args()

    outdir = Path(args.outdir)
    for task in args.tasks:
        _run_task(task, args.model, outdir, args.target_runs)


if __name__ == "__main__":
    main()
