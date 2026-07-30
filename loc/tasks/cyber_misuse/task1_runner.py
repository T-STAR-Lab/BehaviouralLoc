"""Cyber Misuse Task1 runner — 600-question multiple-choice evaluation."""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))

from loc.chat import call_model
from loc.utils.io import atomic_write_json, existing_run_indices, next_missing_run_index
from loc.tasks.cyber_misuse.prompts import build_task1_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("./data/cyber_misuse")
OUTPUT_DIR = Path("./results/cyber_misuse")
MAX_WORKERS = 1


def _process_question(question_data: dict, model_name: str) -> dict:
    try:
        prompt = build_task1_prompt(question_data)
        response = call_model(model_name, [{"role": "user", "content": prompt}])
        n_choices = len(question_data.get("choices", []))
        # Strip thinking block first, then look for a valid choice index
        after_think = re.split(r"</think>", response, flags=re.IGNORECASE)[-1]
        valid = [m for m in re.findall(r"\d+", after_think) if int(m) < n_choices]
        predicted = int(valid[-1]) if valid else -1
        return {
            "id": question_data["id"],
            "question": question_data["question"],
            "choices": question_data["choices"],
            "correct_answer": question_data["answer"],
            "predicted_answer": predicted,
            "raw_response": response,
            "is_correct": predicted == question_data["answer"],
        }
    except Exception as e:
        logger.error(f"Question {question_data.get('id')} failed: {e}")
        return {
            "id": question_data.get("id"),
            "question": question_data.get("question", ""),
            "correct_answer": question_data.get("answer", -1),
            "predicted_answer": -1,
            "error": str(e),
            "is_correct": False,
        }


def run_task1(model_name: str, output_path: Path) -> None:
    input_path = DATA_DIR / "task1.json"
    if not input_path.exists():
        logger.error(f"Task1 data not found: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    logger.info(f"Task1: {len(questions)} questions for {model_name}")

    results = []
    correct_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_question, q, model_name): q for q in questions}
        for future in tqdm(as_completed(futures), total=len(questions), desc="Task1"):
            result = future.result()
            results.append(result)
            if result.get("is_correct"):
                correct_count += 1

    results.sort(key=lambda x: x.get("id", 0))
    accuracy = correct_count / len(questions) if questions else 0.0

    atomic_write_json(output_path, {
        "model": model_name,
        "task": "task1",
        "total_questions": len(questions),
        "correct_answers": correct_count,
        "accuracy": accuracy,
        "results": results,
    })

    logger.info(f"Task1: {correct_count}/{len(questions)} correct ({accuracy:.2%})")
    logger.info(f"Saved to: {output_path}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Cyber Misuse Task1 Evaluation")
    ap.add_argument("--model", required=True)
    ap.add_argument("--target-runs", type=int, default=1)
    args = ap.parse_args()

    run_dir = OUTPUT_DIR / args.model / "task1"
    run_dir.mkdir(parents=True, exist_ok=True)

    existing = existing_run_indices(run_dir)
    while len([i for i in range(1, args.target_runs + 1) if i in set(existing)]) < args.target_runs:
        idx = next_missing_run_index(existing, args.target_runs)
        out = run_dir / f"run_{idx:03d}.json"
        run_task1(args.model, out)
        existing = existing_run_indices(run_dir)


if __name__ == "__main__":
    main()
