"""Sycophancy evaluation runner.

Task1: Multi-level sycophancy test (5 datasets × 5 levels)
Task2-OEQ: Open-ended question evaluation
Task2-PAS: Problem-action-sentence evaluation
"""

import argparse
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List

from tqdm import tqdm

# ---- shared modules ----
import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))

from loc.chat import call_model
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
# ---------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("./data/sycophancy")
DEFAULT_OUTPUT_DIR = Path("./results/sycophancy")

# Task1 datasets
TASK1_DATASETS = ["history.json", "math.json", "logic.json", "med.json", "truth.json"]
TASK1_LEVELS = ["Q1_Simple", "Q2_Ethos", "Q3_Justification", "Q4_Citation", "Q5_Stance_Stress"]

# Task2 datasets
TASK2_OEQ_FILE = DATA_DIR / "OEQ_300.json"
TASK2_PAS_FILE = DATA_DIR / "PAS_200.json"

MAX_WORKERS = 1


# ================== Task1: Multi-level sycophancy ==================

def process_task1_item(item: dict, model_name: str) -> dict:
    """Process one item through all 5 levels."""
    test_cases = item.get("test_cases", {})

    for level in TASK1_LEVELS:
        response_key = f"response_{level}"

        # Skip if already processed
        if response_key in item and item[response_key]:
            continue

        prompt = test_cases.get(level)
        if not prompt:
            item[response_key] = "MISSING_PROMPT"
            continue

        try:
            messages = [{"role": "user", "content": prompt}]
            response = call_model(model_name, messages)
            item[response_key] = response if response else "ERROR: Empty response"
        except Exception as e:
            logger.error(f"Task1 item {item.get('id', 'unknown')} level {level} failed: {e}")
            item[response_key] = f"ERROR: {str(e)}"

    return item


def evaluate_task1(model_name: str, run_path: Path) -> None:
    """Run task1 evaluation for all datasets."""
    results_by_dataset = {}

    for dataset_name in TASK1_DATASETS:
        input_path = DATA_DIR / dataset_name
        if not input_path.exists():
            logger.warning(f"Task1: Dataset {dataset_name} not found, skipping")
            continue

        logger.info(f"Task1: Processing {dataset_name}")

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process items with threading
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(process_task1_item, item, model_name): i
                for i, item in enumerate(data)
            }

            results = [None] * len(data)
            for future in tqdm(as_completed(futures), total=len(futures),
                             desc=f"Task1 {dataset_name}"):
                i = futures[future]
                try:
                    results[i] = future.result()
                except Exception as e:
                    logger.error(f"Task1 {dataset_name} item {i} failed: {e}")
                    results[i] = data[i]

        results_by_dataset[dataset_name] = results

    # Save all results
    atomic_write_json(run_path, {
        "model": model_name,
        "task": "SY.1",
        "datasets": results_by_dataset,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    logger.info(f"Task1 results saved to {run_path}")


# ================== Task2-OEQ: Open-ended questions ==================

def process_task2_oeq_item(item: dict, model_name: str) -> dict:
    """Process one OEQ item."""
    prompt = item.get("prompt", "").strip()

    if not prompt:
        item["response"] = "ERROR: Empty prompt"
        return item

    # Skip if already processed
    if "response" in item and item["response"] and not item["response"].startswith("ERROR"):
        return item

    try:
        messages = [{"role": "user", "content": prompt}]
        response = call_model(model_name, messages)
        item["response"] = response if response else "ERROR: Empty response"
    except Exception as e:
        logger.error(f"Task2-OEQ item {item.get('index', 'unknown')} failed: {e}")
        item["response"] = f"ERROR: {str(e)}"

    return item


def evaluate_task2_oeq(model_name: str, run_path: Path) -> None:
    """Run task2-OEQ evaluation."""
    if not TASK2_OEQ_FILE.exists():
        logger.error(f"Task2-OEQ: Input file {TASK2_OEQ_FILE} not found")
        return

    logger.info("Task2-OEQ: Loading data")
    with open(TASK2_OEQ_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"Task2-OEQ: Processing {len(data)} items")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_task2_oeq_item, item, model_name): i
            for i, item in enumerate(data)
        }

        results = [None] * len(data)
        for future in tqdm(as_completed(futures), total=len(futures), desc="Task2-OEQ"):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as e:
                logger.error(f"Task2-OEQ item {i} failed: {e}")
                results[i] = data[i]

    atomic_write_json(run_path, {
        "model": model_name,
        "task": "SY.2-OEQ",
        "results": results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    logger.info(f"Task2-OEQ results saved to {run_path}")


# ================== Task2-PAS: Problem-action-sentence ==================

def process_task2_pas_item(item: dict, model_name: str) -> dict:
    """Process one PAS item (utterance + sentences)."""
    utterance = item.get("utterance", "").strip()
    sentences = item.get("sentences", "").strip()

    # Combine utterance and sentences
    prompt = f"{utterance}\n\n{sentences}"

    if not utterance and not sentences:
        item["response"] = "ERROR: Empty input"
        return item

    # Skip if already processed
    if "response" in item and item["response"] and not item["response"].startswith("ERROR"):
        return item

    try:
        messages = [{"role": "user", "content": prompt}]
        response = call_model(model_name, messages)
        item["response"] = response if response else "ERROR: Empty response"
    except Exception as e:
        logger.error(f"Task2-PAS item {item.get('index', 'unknown')} failed: {e}")
        item["response"] = f"ERROR: {str(e)}"

    return item


def evaluate_task2_pas(model_name: str, run_path: Path) -> None:
    """Run task2-PAS evaluation."""
    if not TASK2_PAS_FILE.exists():
        logger.error(f"Task2-PAS: Input file {TASK2_PAS_FILE} not found")
        return

    logger.info("Task2-PAS: Loading data")
    with open(TASK2_PAS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logger.info(f"Task2-PAS: Processing {len(data)} items")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(process_task2_pas_item, item, model_name): i
            for i, item in enumerate(data)
        }

        results = [None] * len(data)
        for future in tqdm(as_completed(futures), total=len(futures), desc="Task2-PAS"):
            i = futures[future]
            try:
                results[i] = future.result()
            except Exception as e:
                logger.error(f"Task2-PAS item {i} failed: {e}")
                results[i] = data[i]

    atomic_write_json(run_path, {
        "model": model_name,
        "task": "SY.2-PAS",
        "results": results,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    logger.info(f"Task2-PAS results saved to {run_path}")


# ================== CLI ==================

def parse_args():
    p = argparse.ArgumentParser(description="Sycophancy evaluation")
    p.add_argument("--model", "--model-name", dest="model", required=True,
                   help="Model name to evaluate")
    p.add_argument("--task", choices=["sy1_factual_sycophancy", "sy2_social_sycophancy_oeq", "sy2_social_sycophancy_pas", "all"],
                   default="all", help="Which task to run")
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR),
                   help="Output directory")
    p.add_argument("--target-runs", type=int, default=1,
                   help="Number of runs to complete")
    return p.parse_args()


def _run_loop(label: str, evaluate_fn, model: str, outdir: Path, target_runs: int) -> None:
    """Run evaluation loop with resume support."""
    run_dir = outdir / model / label
    existing = existing_run_indices(run_dir)

    while completed_run_count(existing, target_runs) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        run_path = run_dir / f"run_{idx:03d}.json"
        logger.info(f"[{label}] Starting run {idx:03d}/{target_runs}")

        evaluate_fn(model, run_path)

        existing = existing_run_indices(run_dir)

    logger.info(f"[{label}] All runs completed. Results in {run_dir.resolve()}")


def main():
    args = parse_args()
    outdir = Path(args.outdir)

    if args.task in ("sy1_factual_sycophancy", "all"):
        _run_loop("sy1_factual_sycophancy", evaluate_task1, args.model, outdir, args.target_runs)

    if args.task in ("sy2_social_sycophancy_oeq", "all"):
        _run_loop("sy2_social_sycophancy_oeq", evaluate_task2_oeq, args.model, outdir, args.target_runs)

    if args.task in ("sy2_social_sycophancy_pas", "all"):
        _run_loop("sy2_social_sycophancy_pas", evaluate_task2_pas, args.model, outdir, args.target_runs)


if __name__ == "__main__":
    main()
