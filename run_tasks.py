#!/usr/bin/env python3
"""Top-level entry: dispatch one or more (task, model) jobs to the per-task multi.py.

Examples
--------
    # one task, one model
    python run_tasks.py --tasks power_seeking.inner_value --models gpt-4o-mini

    # multiple tasks × multiple models
    python run_tasks.py --tasks curiosity.epistemic curiosity.decide --models qwen3-8b gpt-4o-mini

    # all subtasks of a family
    python run_tasks.py --tasks self_preservation --models gpt-4o-mini

    # judge / score pass
    python run_tasks.py --tasks power_seeking.inner_value --models gpt-4o-mini --stage judge

    # dry-run: print the resolved subprocess commands and exit
    python run_tasks.py --tasks power_seeking --models gpt-4o-mini --dry-run

The dispatcher just locates `loc/tasks/<family>/<sub>/multi.py` (or `.../single.py`
fallback) and invokes it via the current python with `--model <m>`. No state of
its own; cwd is forced to the repo root so the per-task default paths resolve.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parent

# task -> [subtask, ...]   (subtask "" means flat layout, script in loc/tasks/<task>/)
TASK_TREE: Dict[str, List[str]] = {
    # Flat-layout families (one runner.py per family; subtasks selected via --task).
    "curiosity":         [""],
    "preai":             [""],
    "self_preservation": [""],
    "power_seeking":     [""],
    "perpetuation":      [""],
    "deception":         [""],
    "sandbagging":       [""],
    "sabotage":          [""],
    # Nested families (kept until they're flattened too).
    "sycophancy":        [""],
    "cyber_misuse":      ["task1","task2","task3"],
    "cbrn":              ["b1","b2","b3","c1","c2","c3","r1","r2","r3"],
}

# stage -> (root_dir_under_loc, preferred_script_basenames_in_order)
STAGES = {
    "run":   ("tasks",      ["runner.py", "multi.py", "single.py"]),
    "judge": ("evaluators", ["judge.py", "judge_multi.py"]),
    "score": ("evaluators", ["score_count.py"]),
}


def _resolve_script(stage: str, family: str, sub: str) -> Path | None:
    root, candidates = STAGES[stage]
    base = REPO_ROOT / "loc" / root / family
    if sub:
        base = base / sub
    if stage == "judge":
        # judges often live in <family>/<sub>_judge/ or <family>/.
        for d in (base, base.parent / f"{sub}_judge" if sub else base):
            for name in candidates:
                p = d / name
                if p.exists():
                    return p
    elif stage == "score":
        # score_count usually sits at the family root, not the subtask dir
        for d in (base, REPO_ROOT / "loc" / root / family):
            p = d / candidates[0]
            if p.exists():
                return p
    else:
        for name in candidates:
            p = base / name
            if p.exists():
                return p
    return None


def _expand_tasks(specs: List[str]) -> List[tuple[str, str]]:
    out: List[tuple[str, str]] = []
    for spec in specs:
        if "." in spec:
            family, sub = spec.split(".", 1)
            out.append((family, sub))
            continue
        if spec not in TASK_TREE:
            raise SystemExit(f"unknown task family: {spec!r} (known: {list(TASK_TREE)})")
        for sub in TASK_TREE[spec]:
            out.append((spec, sub))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="dispatch (task × model) jobs")
    ap.add_argument(
        "--tasks", nargs="+", required=True,
        help="task ids: <family> for all sub-tasks, or <family>.<sub> for one",
    )
    ap.add_argument(
        "--models", nargs="+", default=None,
        help="model names (required for run/judge stages; ignored for score)",
    )
    ap.add_argument(
        "--stage", choices=list(STAGES), default="run",
        help="run = task multi/single; judge = LLM-as-judge; score = offline aggregator (ignores --models)",
    )
    ap.add_argument("--dry-run", action="store_true", help="print resolved commands, don't exec")
    ap.add_argument("--continue-on-error", action="store_true", help="don't stop on first non-zero exit")
    ap.add_argument(
        "--target-runs", type=int, default=None,
        help="forward --target-runs N to the dispatched runner.py (run stage only; "
             "honored by deception/sandbagging/sabotage/curiosity/preai/power_seeking/"
             "self_preservation/perpetuation)",
    )
    ap.add_argument(
        "--task", default=None,
        help="forward --task <name> to the dispatched runner.py for families whose "
             "subtasks are now selected via a single runner's --task flag "
             "(curiosity / preai / power_seeking / self_preservation / perpetuation)",
    )
    args = ap.parse_args()

    if args.stage != "score" and not args.models:
        ap.error(f"--models is required for --stage {args.stage}")

    jobs = _expand_tasks(args.tasks)
    failures = 0
    for family, sub in jobs:
        script = _resolve_script(args.stage, family, sub)
        label = f"{family}.{sub}" if sub else family
        if script is None:
            print(f"[skip] {label}: no {args.stage} script found", file=sys.stderr)
            failures += 1
            continue

        models = [None] if args.stage == "score" else args.models
        for model in models:
            cmd = [sys.executable, str(script.relative_to(REPO_ROOT))]
            if model is not None:
                cmd += ["--model", model]
            if args.target_runs is not None and args.stage == "run":
                cmd += ["--target-runs", str(args.target_runs)]
            if args.task is not None and args.stage == "run":
                cmd += ["--task", args.task]
            print(f"[{args.stage}] {label} {'(' + model + ')' if model else ''} -> {' '.join(cmd)}")
            if args.dry_run:
                continue
            rc = subprocess.run(cmd, cwd=REPO_ROOT).returncode
            if rc != 0:
                failures += 1
                print(f"[fail] {label} {model or ''} rc={rc}", file=sys.stderr)
                if not args.continue_on_error:
                    return rc

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
