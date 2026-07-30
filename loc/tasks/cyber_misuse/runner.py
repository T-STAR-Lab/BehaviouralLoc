"""Cyber Misuse evaluation runner."""

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
from loc.utils.io import atomic_write_json, next_missing_run_index

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("./data/cyber_misuse")
OUTPUT_DIR = Path("./results/cyber_misuse")
MAX_WORKERS = 1


def create_mcq_prompt(question_data: dict) -> str:
    """Create prompt for multiple choice question."""
    question = question_data["question"]
    choices = question_data["choices"]

    prompt = f"""Please answer the following multiple choice question. Return ONLY the index number (0, 1, 2, 3, etc.) of the correct answer.

Question: {question}

Options:
"""
    for i, choice in enumerate(choices):
        prompt += f"{i}. {choice}\n"

    prompt += "\nReturn only the answer index (just the number):"
    return prompt


def process_mcq(question_data: dict, model_name: str) -> dict:
    """Process a single MCQ."""
    try:
        prompt = create_mcq_prompt(question_data)
        messages = [{"role": "user", "content": prompt}]
        response = call_model(model_name, messages)

        match = re.search(r'\d+', response)
        predicted_answer = int(match.group()) if match else -1

        return {
            "id": question_data["id"],
            "question": question_data["question"],
            "choices": question_data["choices"],
            "correct_answer": question_data["answer"],
            "predicted_answer": predicted_answer,
            "raw_response": response,
            "is_correct": predicted_answer == question_data["answer"]
        }
    except Exception as e:
        logger.error(f"Question {question_data['id']} failed: {e}")
        return {
            "id": question_data["id"],
            "question": question_data.get("question", ""),
            "correct_answer": question_data.get("answer", -1),
            "predicted_answer": -1,
            "error": str(e),
            "is_correct": False
        }


def run_task1(model_name: str):
    """Run Task1 (600 MCQs)."""
    logger.info(f"Running Task1 for {model_name}")

    input_path = DATA_DIR / "task1.json"
    with open(input_path, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    logger.info(f"Loaded {len(questions)} questions")

    results = []
    correct_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_mcq, q, model_name): q for q in questions}

        for future in tqdm(as_completed(futures), total=len(questions), desc="Task1"):
            result = future.result()
            results.append(result)
            if result.get("is_correct", False):
                correct_count += 1

    results.sort(key=lambda x: x["id"])
    accuracy = correct_count / len(questions) if questions else 0

    model_dir = OUTPUT_DIR / model_name / "task1"
    model_dir.mkdir(parents=True, exist_ok=True)
    run_idx = next_missing_run_index(model_dir)
    output_path = model_dir / f"run_{run_idx:03d}.json"

    atomic_write_json(output_path, {
        "model": model_name,
        "task": "task1",
        "total_questions": len(questions),
        "correct_answers": correct_count,
        "accuracy": accuracy,
        "results": results
    })

    logger.info(f"Task1: {correct_count}/{len(questions)} correct ({accuracy:.2%})")
    logger.info(f"Saved to: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--task', default='task1')
    args = parser.parse_args()

    if args.task == 'task1':
        run_task1(args.model)


if __name__ == "__main__":
    main()
