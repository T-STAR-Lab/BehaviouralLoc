"""LLM-as-judge for Cyber Misuse Task2 (CTF challenge scoring, 0-5 scale).

Reads JUDGE_API_KEY / JUDGE_BASE_URL / JUDGE_MODEL from the environment.
Falls back to the same OpenAI-compatible endpoint used by other judges.
"""

import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))

from dotenv import load_dotenv
load_dotenv(_repo_root / "env" / ".env", override=True)

from loc.tasks.cyber_misuse.prompts import build_task2_judge_messages
from loc.utils.io import atomic_write_json, existing_run_indices, next_missing_run_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4.1")
_MAX_RETRIES = int(os.getenv("JUDGE_MAX_RETRIES", "3"))
_DELAY = float(os.getenv("JUDGE_DELAY", "0.5"))
_MAX_WORKERS = 3

RESULTS_DIR = Path("./results/cyber_misuse")
RUN_FILE_RE = re.compile(r"^run_(\d+)\.json$")


def _judge_client():
    from openai import OpenAI
    return OpenAI(
        api_key=os.getenv("JUDGE_API_KEY", ""),
        base_url=os.getenv("JUDGE_BASE_URL") or None,
        timeout=120.0,
    )


def _score_item(item: dict) -> dict:
    """Call the judge model and return {score, reason}."""
    messages = build_task2_judge_messages(item)
    for attempt in range(_MAX_RETRIES):
        try:
            response = _judge_client().chat.completions.create(
                model=_JUDGE_MODEL,
                messages=messages,
                temperature=0,
            )
            text = response.choices[0].message.content.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = re.sub(r"^```[a-z]*\n?", "", text)
                text = re.sub(r"\n?```$", "", text.strip())
            evaluation = json.loads(text)
            if "score" not in evaluation:
                raise ValueError("Response missing 'score' field")
            return {"score": int(evaluation["score"]), "reason": evaluation.get("reason", "")}
        except Exception as e:
            logger.warning(f"Judge attempt {attempt + 1}/{_MAX_RETRIES} failed for {item.get('id')}: {e}")
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_DELAY * (attempt + 1))
    return {"score": 0, "reason": f"Judge failed after {_MAX_RETRIES} retries"}


def judge_run(run_path: Path, output_path: Path) -> None:
    """Score all items in a task2 run file and write judged results."""
    with open(run_path, "r", encoding="utf-8") as f:
        run_data = json.load(f)

    items = run_data.get("results", [])
    logger.info(f"Judging {len(items)} items from {run_path.name}")

    judged = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(_score_item, item): item for item in items}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Judging"):
            item = futures[future]
            evaluation = future.result()
            judged.append({
                "id": item.get("id"),
                "category": item.get("category", ""),
                "score": evaluation["score"],
                "reason": evaluation["reason"],
                "prompt": item.get("prompt", ""),
                "ground_truth": item.get("ground_truth", ""),
                "model_answer": item.get("model_answer", ""),
            })

    judged.sort(key=lambda x: (x.get("category", ""), x.get("id", "")))
    scores = [j["score"] for j in judged]

    # Per-category breakdown
    categories: dict = {}
    for j in judged:
        cat = j.get("category", "unknown")
        categories.setdefault(cat, []).append(j["score"])
    category_stats = {
        cat: {
            "count": len(vals),
            "average": sum(vals) / len(vals) if vals else 0,
            "distribution": {str(s): vals.count(s) for s in range(6)},
        }
        for cat, vals in categories.items()
    }

    atomic_write_json(output_path, {
        "source_run": str(run_path),
        "model": run_data.get("model", ""),
        "task": "CY.2",
        "total": len(judged),
        "average_score": sum(scores) / len(scores) if scores else 0,
        "score_distribution": {str(s): scores.count(s) for s in range(6)},
        "category_stats": category_stats,
        "evaluations": judged,
    })

    logger.info(f"Average score: {sum(scores)/len(scores):.3f} | Saved to: {output_path}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Cyber Misuse Task2 Judge")
    ap.add_argument("--model", required=True)
    ap.add_argument("--target-runs", type=int, default=1)
    args = ap.parse_args()

    run_dir = RESULTS_DIR / args.model / "cy2_ctf_challenge_solving"
    judge_dir = RESULTS_DIR / args.model / "cy2_ctf_challenge_solving_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)

    existing_runs = existing_run_indices(run_dir)
    existing_judged = existing_run_indices(judge_dir)

    for idx in existing_runs:
        if idx in set(existing_judged):
            continue
        run_path = run_dir / f"run_{idx:03d}.json"
        out_path = judge_dir / f"run_{idx:03d}.json"
        logger.info(f"Judging run {idx:03d}")
        judge_run(run_path, out_path)


if __name__ == "__main__":
    main()
