#!/usr/bin/env python3
"""Batch driver for running demo task.py files across (model, demo, variant) combinations.

Jobs are executed serially in the order: model x demo x variant.

Examples:
    # all dims, all demos, all 20 variants, one model
    python run_batch.py --models qwen3-14b

    # one dim
    python run_batch.py --models qwen3-14b --dim Self-Improvement

    # one or more demos, specific variants
    python run_batch.py --models qwen3-14b --demos Self-Improvement/demo1 --variants 1,3,5-10
    python run_batch.py --models qwen3-14b --demos Self-Improvement/demo1 Malignant-Competition/demo3

    # multiple models
    python run_batch.py --models qwen3-14b deepseek-v3.2
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
from typing import List

REPO_ROOT = pathlib.Path(__file__).resolve().parent
DEMOS_ROOT = REPO_ROOT / "demos"
DIMS = [
    "Self-Improvement",
    "Malignant-Competition",
    "Covert-Planning",
    "Cooperative-Jailbreaking",
]
DEMOS_PER_DIM = 5
VARIANTS_PER_DEMO = 20


def parse_variant_spec(spec: str) -> List[int]:
    """Parse '1,3,5-10' into [1,3,5,6,7,8,9,10]."""
    out: List[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(chunk))
    return sorted(set(out))


def resolve_demos(dim: str | None, demos: List[str] | None) -> List[str]:
    if demos:
        return list(demos)
    dims = [dim] if dim else DIMS
    return [f"{d}/demo{i}" for d in dims for i in range(1, DEMOS_PER_DIM + 1)]


def resolve_variants(spec: str | None) -> List[int]:
    if spec:
        return parse_variant_spec(spec)
    return list(range(1, VARIANTS_PER_DEMO + 1))


def run_one(model: str, demo_id: str, variant: int,
            max_tokens: int, max_retries: int, time_limit: int) -> tuple[str, int]:
    task_py = DEMOS_ROOT / demo_id / "task.py"
    if not task_py.exists():
        return (f"{demo_id} model={model} variant={variant}", -1)

    cmd = [
        sys.executable, str(task_py),
        "--model-name", model,
        "--variant", str(variant),
        "--max-tokens", str(max_tokens),
        "--max-retries", str(max_retries),
        "--time-limit", str(time_limit),
    ]

    tag = f"{demo_id} model={model} variant={variant}"
    print(f"[RUN] {tag}")
    result = subprocess.run(cmd, cwd=str(task_py.parent))
    return (tag, result.returncode)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", required=True, nargs="+", help="One or more model names, space-separated")

    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--dim", help="Run all demos in this dim only")
    scope.add_argument("--demos", nargs="+",
                       help="One or more demos, space-separated (e.g. Self-Improvement/demo1 Malignant-Competition/demo3)")

    ap.add_argument("--variants", help='Variant spec, e.g. "1,3,5-10". Default: 1-20')

    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--max-retries", type=int, default=5)
    ap.add_argument("--time-limit", type=int, default=1800)

    args = ap.parse_args()

    models = list(args.models)
    demos = resolve_demos(args.dim, args.demos)
    variants = resolve_variants(args.variants)

    jobs = [(m, d, v) for m in models for d in demos for v in variants]
    print(f"[INFO] {len(jobs)} job(s): models={models} demos={len(demos)} variants={len(variants)}")

    results = [run_one(m, d, v, args.max_tokens, args.max_retries, args.time_limit) for m, d, v in jobs]

    failed = [t for t, rc in results if rc != 0]
    print(f"\n[SUMMARY] {len(results) - len(failed)}/{len(results)} succeeded")
    for t in failed:
        print(f"  FAILED: {t}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
