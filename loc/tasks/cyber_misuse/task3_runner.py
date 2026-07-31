"""Cyber Misuse Task3 runner — Canary Exploit (PurpleLlama) generation.

Each item in cy3_vulnerability_exploitation.json has:
  mutated_prompt, challenge_type, language, code, answer

The runner calls call_model() and saves responses in the format expected
by the canary scorer (verify_response.py compatible).
"""

import json
import logging
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
from loc.tasks.cyber_misuse.prompts import build_task3_prompt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_PATH = Path("./data/cyber_misuse/cy3_vulnerability_exploitation.json")
OUTPUT_DIR = Path("./results/cyber_misuse")
MAX_WORKERS = 1


def _process_item(item: dict, model_name: str) -> dict:
    """Call model and return a scorer-compatible result dict."""
    try:
        prompt = build_task3_prompt(item)
        response = call_model(model_name, [{"role": "user", "content": prompt}])
        return {
            # Fields the canary scorer reads
            "mutated_prompt": item["mutated_prompt"],
            "challenge_type": item["challenge_type"],
            "language": item["language"],
            "code": item["code"],
            "answer": item["answer"],
            "response": response,
            "model": model_name,
            # Extra bookkeeping
            "success": bool(response),
            "error": None,
        }
    except Exception as e:
        logger.error(f"Item failed ({item.get('challenge_type')}/{item.get('language')}): {e}")
        return {
            "mutated_prompt": item.get("mutated_prompt", ""),
            "challenge_type": item.get("challenge_type", ""),
            "language": item.get("language", ""),
            "code": item.get("code", ""),
            "answer": item.get("answer", ""),
            "response": "",
            "model": model_name,
            "success": False,
            "error": str(e),
        }


def run_task3(model_name: str, output_path: Path) -> None:
    if not DATA_PATH.exists():
        logger.error(f"Task3 data not found: {DATA_PATH}")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    logger.info(f"Task3: {len(items)} items for {model_name}")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_process_item, item, model_name): item for item in items}
        for future in tqdm(as_completed(futures), total=len(items), desc="Task3"):
            results.append(future.result())

    success_count = sum(1 for r in results if r["success"])

    atomic_write_json(output_path, {
        "model": model_name,
        "task": "CY.3",
        "total": len(items),
        "success_count": success_count,
        "results": results,
    })

    logger.info(f"Task3: {success_count}/{len(items)} responses collected")
    logger.info(f"Saved to: {output_path}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Cyber Misuse Task3 Evaluation")
    ap.add_argument("--model", required=True)
    ap.add_argument("--target-runs", type=int, default=1)
    args = ap.parse_args()

    run_dir = OUTPUT_DIR / args.model / "cy3_vulnerability_exploitation"
    run_dir.mkdir(parents=True, exist_ok=True)

    existing = existing_run_indices(run_dir)
    while len([i for i in range(1, args.target_runs + 1) if i in set(existing)]) < args.target_runs:
        idx = next_missing_run_index(existing, args.target_runs)
        out = run_dir / f"run_{idx:03d}.json"
        run_task3(args.model, out)
        existing = existing_run_indices(run_dir)


if __name__ == "__main__":
    main()
