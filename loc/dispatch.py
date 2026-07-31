"""Benchmark dispatch CLI implementation."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List

from loc.task_registry import (
    TASKS as CANONICAL_TASKS,
    RunSpec,
    all_dimensions,
    all_sections,
    find_by_dimensions,
    find_by_ids,
    find_by_sections,
    format_task_table,
    run_specs_for,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

STAGES = {
    "run": ("tasks", ["runner.py", "multi.py", "single.py"]),
    "judge": ("evaluators", ["judge.py", "judge_multi.py"]),
    "score": ("evaluators", ["score_count.py"]),
}


def _resolve_script(stage: str, family: str, sub: str) -> Path | None:
    root, candidates = STAGES[stage]
    base = REPO_ROOT / "loc" / root / family
    if sub:
        base = base / sub
    if stage == "judge":
        for d in (base, base.parent / f"{sub}_judge" if sub else base):
            for name in candidates:
                path = d / name
                if path.exists():
                    return path
    elif stage == "score":
        for d in (base, REPO_ROOT / "loc" / root / family):
            path = d / candidates[0]
            if path.exists():
                return path
    else:
        for name in candidates:
            path = base / name
            if path.exists():
                return path
    return None


def _expand_task_groups(groups: List[str]) -> List[RunSpec]:
    tasks = find_by_dimensions(groups)
    found = {task.dimension.lower() for task in tasks} | {task.family.lower() for task in tasks}
    missing = [group for group in groups if group.lower() not in found]
    if missing:
        raise SystemExit(f"unknown task group(s): {', '.join(missing)}")
    return run_specs_for(tasks, include_nonimplemented=True)


def _dedupe_specs(specs: List[RunSpec]) -> List[RunSpec]:
    out: List[RunSpec] = []
    seen: set[RunSpec] = set()
    for spec in specs:
        if spec in seen:
            continue
        seen.add(spec)
        out.append(spec)
    return out


def _score_specs_for(run_specs: List[RunSpec]) -> List[RunSpec]:
    out: List[RunSpec] = []
    seen: set[str] = set()
    for spec in run_specs:
        key = spec.task_id
        if key in seen:
            continue
        seen.add(key)
        out.append(spec)
    return out


def _resolve_run_spec_script(stage: str, spec: RunSpec) -> Path | None:
    if stage == "score":
        return REPO_ROOT / "score_tasks.py"
    if spec.script:
        return REPO_ROOT / spec.script
    return _resolve_script(stage, spec.family, spec.subtask)


def _score_command(args: argparse.Namespace, run_jobs: List[RunSpec]) -> list[str]:
    cmd = [sys.executable, "score_tasks.py"]
    ids: list[str] = []
    dimensions: list[str] = []
    for spec in _score_specs_for(run_jobs):
        if spec.task_id not in ids:
            ids.append(spec.task_id)
    if ids:
        cmd += ["--ids", *ids]
    if dimensions:
        cmd += ["--dimensions", *dimensions]
    if args.models:
        cmd += ["--models", *args.models]
    return cmd


def _judge_commands(args: argparse.Namespace, run_jobs: List[RunSpec]) -> list[list[str]]:
    scripts: list[tuple[str, list[str]]] = []

    def add(script: str, extra: list[str] | None = None) -> None:
        item = (script, extra or [])
        if item not in scripts:
            scripts.append(item)

    for spec in run_jobs:
        if spec.task_id == "PB.1" and spec.component == "reasoning":
            add("loc/evaluators/judges/preai_explicit_why.py")
        elif spec.task_id == "PS.2":
            add("loc/evaluators/judges/power_seeking_instrumental.py")
        elif spec.task_id == "AU.1":
            add("loc/evaluators/judges/perpetuation.py")
        elif spec.task_id == "CY.2":
            add("loc/evaluators/judges/cyber_ctf.py")
        elif spec.task_id == "CY.3":
            add("loc/evaluators/judges/cyber_vulnerability.py")
        elif spec.task_id == "CB.1" and spec.component == "nuclear":
            add("loc/evaluators/judges/cbrn_open.py", ["--component", "cb1_nuclear"])
        elif spec.task_id == "CB.3" and spec.component == "nuclear":
            add("loc/evaluators/judges/cbrn_open.py", ["--component", "cb3_nuclear"])

    commands: list[list[str]] = []
    for script, extra in scripts:
        for model in args.models or []:
            commands.append([sys.executable, script, "--model", model, *extra])
    return commands


def _selected_run_specs(args: argparse.Namespace) -> List[RunSpec]:
    specs: List[RunSpec] = []
    if args.tasks:
        specs.extend(_expand_task_groups(args.tasks))
    if args.ids:
        specs.extend(run_specs_for(find_by_ids(args.ids)))
    selected_groups = []
    if args.dimensions:
        selected_groups.extend(find_by_dimensions(args.dimensions))
    if args.sections:
        selected_groups.extend(find_by_sections(args.sections))
    if selected_groups:
        skipped = [task for task in selected_groups if task.status != "implemented"]
        for task in skipped:
            print(f"[skip] {task.id} {task.name}: {task.status} ({task.notes})", file=sys.stderr)
        specs.extend(run_specs_for(selected_groups, include_nonimplemented=True))
    if not specs:
        raise SystemExit("select at least one of --tasks, --ids, --dimensions, or --sections")
    return _dedupe_specs(specs)


def _print_list(status: str | None = None) -> None:
    tasks = list(CANONICAL_TASKS)
    if status:
        tasks = [task for task in tasks if task.status == status]
    print(format_task_table(tasks))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="dispatch benchmark jobs")
    parser.add_argument("--tasks", nargs="+", default=None, help="task groups/dimensions, e.g. curiosity cbrn sandbagging")
    parser.add_argument("--ids", nargs="+", default=None, help="canonical task IDs, e.g. CU.1 PS.2 SB.1")
    parser.add_argument("--dimensions", nargs="+", default=None, help=f"canonical dimensions/families: {all_dimensions()}")
    parser.add_argument("--sections", nargs="+", default=None, help=f"canonical sections: {all_sections()}")
    parser.add_argument("--list", action="store_true", help="print the canonical task registry and exit")
    parser.add_argument("--status", default=None, help="filter --list by status: implemented, missing, external")
    parser.add_argument("--models", nargs="+", default=None, help="model names; required for run/judge")
    parser.add_argument("--stage", choices=list(STAGES), default="run")
    parser.add_argument("--dry-run", action="store_true", help="print resolved commands, do not execute")
    parser.add_argument("--continue-on-error", action="store_true", help="do not stop on first non-zero exit")
    parser.add_argument("--target-runs", type=int, default=None, help="forward --target-runs N to run-stage scripts")
    parser.add_argument("--task", default=None, help="override/forward a single --task argument to run-stage scripts")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list:
        _print_list(args.status)
        return 0
    if args.stage != "score" and not args.models:
        raise SystemExit(f"--models is required for --stage {args.stage}")

    run_jobs = _selected_run_specs(args)
    if args.stage == "judge":
        commands = _judge_commands(args, run_jobs)
        if not commands:
            print("[judge] no judge step is required for the selected tasks", flush=True)
            return 0
        failures = 0
        for cmd in commands:
            print(f"[judge] canonical -> {' '.join(cmd)}", flush=True)
            if args.dry_run:
                continue
            rc = subprocess.run(cmd, cwd=REPO_ROOT).returncode
            if rc != 0:
                failures += 1
                print(f"[fail] judge rc={rc}: {' '.join(cmd)}", file=sys.stderr)
                if not args.continue_on_error:
                    return rc
        return 1 if failures else 0

    if args.stage == "score":
        cmd = _score_command(args, run_jobs)
        print(f"[score] canonical -> {' '.join(cmd)}", flush=True)
        if args.dry_run:
            return 0
        return subprocess.run(cmd, cwd=REPO_ROOT).returncode

    jobs = _score_specs_for(run_jobs) if args.stage == "score" else run_jobs
    failures = 0
    for spec in jobs:
        script = _resolve_run_spec_script(args.stage, spec)
        label = spec.label
        if script is None:
            print(f"[skip] {label}: no {args.stage} script found", file=sys.stderr)
            failures += 1
            continue

        models = [None] if args.stage == "score" else args.models
        for model in models:
            cmd = [sys.executable, str(script.relative_to(REPO_ROOT))]
            if args.stage == "score":
                if spec.task_id.startswith("legacy."):
                    cmd += ["--dimensions", spec.family]
                else:
                    cmd += ["--ids", spec.task_id]
                if args.models:
                    cmd += ["--models", *args.models]
            elif model is not None:
                cmd += ["--model", model]
            if args.target_runs is not None and args.stage == "run":
                cmd += ["--target-runs", str(args.target_runs)]
            task_arg = args.task if args.task is not None else spec.task_arg
            if task_arg is not None and args.stage == "run":
                cmd += ["--task", task_arg]
            if spec.extra_args and args.stage == "run":
                cmd += list(spec.extra_args)
            print(f"[{args.stage}] {label} {'(' + model + ')' if model else ''} -> {' '.join(cmd)}", flush=True)
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
    raise SystemExit(main())
