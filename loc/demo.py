"""Run a fixed three-question subset of the released CY.1 benchmark data."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from loc.chat import call_model
from loc.tasks.cyber_misuse.prompts import build_task1_prompt


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "cyber_misuse" / "cy1_cybersecurity_knowledge.json"
DEMO_SIZE = 3


def _load_questions() -> list[dict]:
    if not DATA_PATH.exists():
        raise SystemExit(
            "Demo data not found. Download the BehaviouralLoC dataset into data/; "
            f"expected: {DATA_PATH}"
        )

    questions = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(questions, list) or len(questions) < DEMO_SIZE:
        raise SystemExit(f"Demo requires at least {DEMO_SIZE} CY.1 questions in {DATA_PATH}")

    required = {"id", "question", "choices", "answer"}
    selected = questions[:DEMO_SIZE]
    for index, question in enumerate(selected):
        missing = required.difference(question)
        if missing:
            missing_names = ", ".join(sorted(missing))
            raise SystemExit(f"Invalid CY.1 item at index {index}: missing {missing_names}")
    return selected


def _parse_answer(response: str, choice_count: int) -> int:
    final_text = re.split(r"</think>", response, flags=re.IGNORECASE)[-1]
    valid = [int(value) for value in re.findall(r"\d+", final_text) if int(value) < choice_count]
    return valid[-1] if valid else -1


def run_demo(models: list[str], dry_run: bool = False) -> int:
    questions = _load_questions()
    if dry_run:
        for item in questions:
            item_id = item["id"]
            question = item["question"]
            print(f"[demo] CY.1 id={item_id}: {question}")
        print(f"[demo] models={models}; no model calls were made")
        return 0

    output = {
        "mode": "aspects-demo",
        "task": "CY.1",
        "source": "data/cyber_misuse/cy1_cybersecurity_knowledge.json",
        "sample_count": DEMO_SIZE,
        "models": {},
    }
    failed = False

    for model in models:
        rows = []
        correct_count = 0
        for item in questions:
            response = call_model(
                model,
                [{"role": "user", "content": build_task1_prompt(item)}],
            )
            predicted = _parse_answer(response, len(item["choices"]))
            expected = item["answer"]
            item_id = item["id"]
            is_correct = predicted == expected
            correct_count += int(is_correct)
            failed = failed or not response
            rows.append(
                {
                    "id": item_id,
                    "question": item["question"],
                    "choices": item["choices"],
                    "correct_answer": expected,
                    "predicted_answer": predicted,
                    "raw_response": response,
                    "is_correct": is_correct,
                }
            )
            print(
                f"[demo] model={model} id={item_id} predicted={predicted} "
                f"expected={expected} correct={is_correct}"
            )

        accuracy = correct_count / DEMO_SIZE
        output["models"][model] = {
            "correct_answers": correct_count,
            "accuracy": accuracy,
            "results": rows,
        }
        print(f"[demo] model={model} accuracy={correct_count}/{DEMO_SIZE} ({accuracy:.2%})")

    output_dir = REPO_ROOT / "results" / "demo"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = output_dir / f"aspects_demo_{timestamp}.json"
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[done] results -> {output_path}")
    return 1 if failed else 0
