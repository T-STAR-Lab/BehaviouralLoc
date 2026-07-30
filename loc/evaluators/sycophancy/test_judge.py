#!/usr/bin/env python3
"""Test script for sycophancy judge system.

This script tests the judge system without running actual evaluations.
"""

import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parents[4]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import after adding to path
import importlib.util
spec = importlib.util.spec_from_file_location("judge", Path(__file__).parent / "judge.py")
judge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(judge)

REPO_ROOT = judge.REPO_ROOT
RESULTS_DIR = judge.RESULTS_DIR
NEO_DIR = judge.NEO_DIR
TASK2_DIR = judge.TASK2_DIR
MODEL_MAPPING = judge.MODEL_MAPPING
_list_runs = judge._list_runs

def test_paths():
    """Test that all required paths exist."""
    print("Testing paths...")
    print(f"  REPO_ROOT: {REPO_ROOT}")
    print(f"    Exists: {REPO_ROOT.exists()}")

    print(f"  RESULTS_DIR: {RESULTS_DIR}")
    print(f"    Exists: {RESULTS_DIR.exists()}")

    print(f"  NEO_DIR: {NEO_DIR}")
    print(f"    Exists: {NEO_DIR.exists()}")
    print(f"    eval_sycophancy.py: {(NEO_DIR / 'eval_sycophancy.py').exists()}")
    print(f"    count.py: {(NEO_DIR / 'count.py').exists()}")

    print(f"  TASK2_DIR: {TASK2_DIR}")
    print(f"    Exists: {TASK2_DIR.exists()}")
    print(f"    OEQ_judge.py: {(TASK2_DIR / 'OEQ_judge.py').exists()}")
    print(f"    PAS_judge.py: {(TASK2_DIR / 'PAS_judge.py').exists()}")
    print()


def test_model_runs():
    """Test finding model runs."""
    print("Testing model runs...")

    for display_name, model_name in list(MODEL_MAPPING.items())[:3]:  # Test first 3 models
        print(f"\n  Model: {display_name} ({model_name})")
        model_path = RESULTS_DIR / model_name

        if not model_path.exists():
            print(f"    No results directory found")
            continue

        # Check Task1
        task1_runs = _list_runs(model_path, "task1")
        print(f"    Task1 runs: {len(task1_runs)}")
        if task1_runs:
            print(f"      Latest: run_{max(task1_runs.keys()):03d}.json")

        # Check Task2-OEQ
        task2_oeq_runs = _list_runs(model_path, "task2-oeq")
        print(f"    Task2-OEQ runs: {len(task2_oeq_runs)}")
        if task2_oeq_runs:
            print(f"      Latest: run_{max(task2_oeq_runs.keys()):03d}.json")

        # Check Task2-PAS
        task2_pas_runs = _list_runs(model_path, "task2-pas")
        print(f"    Task2-PAS runs: {len(task2_pas_runs)}")
        if task2_pas_runs:
            print(f"      Latest: run_{max(task2_pas_runs.keys()):03d}.json")

    print()


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        import pandas as pd
        print("  [OK] pandas")
    except ImportError:
        print("  [FAIL] pandas (required)")

    try:
        from dotenv import load_dotenv
        print("  [OK] python-dotenv")
    except ImportError:
        print("  [FAIL] python-dotenv (required)")

    try:
        from tqdm import tqdm
        print("  [OK] tqdm")
    except ImportError:
        print("  [FAIL] tqdm (required)")

    try:
        from tenacity import retry
        print("  [OK] tenacity")
    except ImportError:
        print("  [FAIL] tenacity (required)")

    try:
        from openai import OpenAI
        print("  [OK] openai")
    except ImportError:
        print("  [FAIL] openai (required)")

    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Sycophancy Judge System Test")
    print("=" * 60)
    print()

    test_imports()
    test_paths()
    test_model_runs()

    print("=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
