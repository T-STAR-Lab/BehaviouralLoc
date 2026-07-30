"""curiosity — aggregate ``results/curiosity/<model>/<task>/run_NNN.json``.

Averages ``ratio_A`` (decide) and ``ratio`` (epistemic) across all runs of each
model, then prints the combined CURIOSITYSCORE.
"""

import argparse
import json
import statistics
from pathlib import Path

DEFAULT_RESULTS = Path("./results/curiosity")
SUBTASKS = ["decide", "epistemic"]


def _runs_of(model_dir: Path, task: str):
    task_dir = model_dir / task
    if not task_dir.is_dir():
        return []
    return sorted(task_dir.glob("run_*.json"))


def _summary_value(run_path: Path, task: str):
    with open(run_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    summary = data.get("summary", {})
    if task == "decide":
        return summary.get("ratio_A")
    if task == "epistemic":
        return summary.get("ratio")
    return None


def _discover_models(base: Path):
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith("_"))


def parse_args():
    p = argparse.ArgumentParser(description="curiosity — aggregate run_NNN.json")
    p.add_argument("--outdir", default=str(DEFAULT_RESULTS))
    p.add_argument("--model", default=None, help="restrict to a single model")
    return p.parse_args()


def main():
    args = parse_args()
    base = Path(args.outdir)
    models = [args.model] if args.model else _discover_models(base)
    if not models:
        print(f"[curiosity] no model dirs under {base}")
        return
    for model in models:
        mdir = base / model
        per_task = {}
        for task in SUBTASKS:
            vals = [v for v in (_summary_value(p, task) for p in _runs_of(mdir, task)) if v is not None]
            per_task[task] = vals
        print("=" * 80)
        print(f"Model: {model}")
        if not any(per_task.values()):
            print("  (no runs found)")
            continue
        for task, vals in per_task.items():
            if not vals:
                print(f"  {task}: no runs")
                continue
            print(f"  {task}: runs={len(vals)} mean={statistics.fmean(vals):.4f}")
        if per_task["decide"] and per_task["epistemic"]:
            avg = (statistics.fmean(per_task["decide"]) + statistics.fmean(per_task["epistemic"])) / 2
            print(f"  CURIOSITYSCORE: {avg:.4f}")


if __name__ == "__main__":
    main()
