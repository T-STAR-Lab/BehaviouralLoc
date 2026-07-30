"""Cyber Misuse Task2 runner — CTF challenge generation (5 categories)."""

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
from loc.tasks.cyber_misuse.prompts import build_task2_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path("./data/cyber_misuse")
OUTPUT_DIR = Path("./results/cyber_misuse")
MAX_WORKERS = 1

CATEGORIES = ["crypto", "forensics", "pwn", "rev", "web"]


def _load_category(category: str) -> list:
    """Load task2 data for one category, stripping markdown fences if present."""
    path = DATA_DIR / f"task2_{category}.json"
    if not path.exists():
        logger.error(f"Task2 data not found: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()
    # Strip ```json ... ``` fences that some data files contain
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw.strip())
    return json.loads(raw)


def _process_item(item: dict, model_name: str) -> dict:
    try:
        prompt = build_task2_prompt(item)
        response = call_model(model_name, [{"role": "user", "content": prompt}])
        return {
            "id": item["id"],
            "category": item.get("category", ""),
            "prompt": item["prompt"],
            "ground_truth": item.get("ground_truth", ""),
            "model_answer": response,
            "success": bool(response),
            "error": None,
        }
    except Exception as e:
        logger.error(f"Item {item.get('id')} failed: {e}")
        return {
            "id": item.get("id"),
            "category": item.get("category", ""),
            "prompt": item.get("prompt", ""),
            "ground_truth": item.get("ground_truth", ""),
            "model_answer": "",
            "success": False,
            "error": str(e),
        }


def run_task2_category(model_name: str, category: str, output_path: Path) -> None:
    items = _load_category(category)
    if not items:
        return

    logger.info(f"Task2/{category}: {len(items)} items for {model_name}")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_item, item, model_name): item for item in items}
        for future in tqdm(as_completed(futures), total=len(items), desc=f"Task2/{category}"):
            results.append(future.result())

    results.sort(key=lambda x: x.get("id", ""))
    success_count = sum(1 for r in results if r["success"])

    atomic_write_json(output_path, {
        "model": model_name,
        "task": "task2",
        "category": category,
        "total": len(items),
        "success_count": success_count,
        "results": results,
    })

    logger.info(f"Task2/{category}: {success_count}/{len(items)} succeeded")
    logger.info(f"Saved to: {output_path}")


def run_task2(model_name: str, output_path: Path) -> None:
    """Run all 5 categories and save a combined result file."""
    all_results = []
    for cat in CATEGORIES:
        items = _load_category(cat)
        if not items:
            continue
        logger.info(f"Task2/{cat}: {len(items)} items for {model_name}")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(_process_item, item, model_name): item for item in items}
            for future in tqdm(as_completed(futures), total=len(items), desc=f"Task2/{cat}"):
                all_results.append(future.result())

    all_results.sort(key=lambda x: (x.get("category", ""), x.get("id", "")))
    success_count = sum(1 for r in all_results if r["success"])

    atomic_write_json(output_path, {
        "model": model_name,
        "task": "task2",
        "total": len(all_results),
        "success_count": success_count,
        "results": all_results,
    })

    logger.info(f"Task2 all: {success_count}/{len(all_results)} succeeded")
    logger.info(f"Saved to: {output_path}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Cyber Misuse Task2 Evaluation")
    ap.add_argument("--model", required=True)
    ap.add_argument("--category", default="all",
                    help=f"Category to run: {CATEGORIES} or 'all'")
    ap.add_argument("--target-runs", type=int, default=1)
    args = ap.parse_args()

    run_dir = OUTPUT_DIR / args.model / "task2"
    run_dir.mkdir(parents=True, exist_ok=True)

    existing = existing_run_indices(run_dir)
    while len([i for i in range(1, args.target_runs + 1) if i in set(existing)]) < args.target_runs:
        idx = next_missing_run_index(existing, args.target_runs)
        out = run_dir / f"run_{idx:03d}.json"
        run_task2(args.model, out)
        existing = existing_run_indices(run_dir)


if __name__ == "__main__":
    main()
