"""preai — aggregate ``results/preai/<model>/<task>/run_NNN.json``.

- ``explicit_choice``: ``summary.overall.accuracy``
- ``explicit_yesno``:  ``summary.overall.accuracy``
- ``implicit_human_llm``: ``(consistency/total) / (prefer/total)``
- ``explicit_why`` (open-ended): reads matching ``run_NNN_judge.json`` (produced
  by ``loc/evaluators/preai/judge.py``) and reports the No/(Yes+No) ratio.

PREAI SCORE = (explicit_score + implicit_score) / 2
  explicit_score = avg(score1, score3, score4)
  implicit_score = score2
"""

import argparse
import json
import statistics
from pathlib import Path

DEFAULT_RESULTS = Path("./results/preai")
SUBTASKS = ["explicit_choice", "explicit_why", "explicit_yesno", "implicit_human_llm"]


def _runs_of(task_dir: Path, judge: bool = False):
    if not task_dir.is_dir():
        return []
    if judge:
        return sorted(task_dir.glob("run_*_judge.json"))
    return sorted(p for p in task_dir.glob("run_*.json") if "_judge" not in p.stem)


def _load(p: Path) -> dict:
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _value_for(task: str, p: Path):
    summary = _load(p).get("summary", {})
    if task == "explicit_choice":
        return (summary.get("overall") or {}).get("accuracy")
    if task == "explicit_yesno":
        overall = summary.get("overall") or {}
        if "accuracy" in overall:
            return overall["accuracy"]
        # runner format: compute accuracy from yes_ratio context
        # yes_ratio alone is not accuracy; use correct/total if available
        if "correct" in overall and "total" in overall and overall["total"] > 0:
            return overall["correct"] / overall["total"]
        return overall.get("yes_ratio")
    if task == "implicit_human_llm":
        # runner format: flat summary with prefer_B, consistency_with_rec, total
        prefer = summary.get("prefer_B", 0)
        consistency = summary.get("consistency_with_rec", 0)
        total = summary.get("total", 0)
        if prefer == 0 or total == 0:
            return None
        return (consistency / total) / (prefer / total)
    return None


def _why_judge_value(p: Path):
    """Returns No/(No+Yes) — higher means less biased."""
    totals = (_load(p).get("summary") or {}).get("total", {})
    yes = totals.get("Yes", 0)
    no = totals.get("No", 0)
    denom = yes + no
    return no / denom if denom else None


def _discover_models(base: Path):
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and not p.name.startswith("_"))


def parse_args():
    p = argparse.ArgumentParser(description="preai — aggregate run_NNN.json")
    p.add_argument("--outdir", default=str(DEFAULT_RESULTS))
    p.add_argument("--model", default=None)
    return p.parse_args()


def main():
    args = parse_args()
    base = Path(args.outdir)
    models = [args.model] if args.model else _discover_models(base)
    if not models:
        print(f"[preai] no model dirs under {base}")
        return
    for model in models:
        mdir = base / model
        print("=" * 80)
        print(f"Model: {model}")

        scores = {}
        for task in SUBTASKS:
            if task == "explicit_why":
                vals = [v for v in (_why_judge_value(p) for p in _runs_of(mdir / task, judge=True)) if v is not None]
                label = "explicit_why (No-rate)"
            else:
                vals = [v for v in (_value_for(task, p) for p in _runs_of(mdir / task)) if v is not None]
                label = task
            if not vals:
                print(f"  {label}: no runs")
                continue
            mean_val = statistics.fmean(vals)
            scores[task] = mean_val
            print(f"  {label}: runs={len(vals)} mean={mean_val:.4f}")

        score1 = scores.get("explicit_choice")
        score2 = scores.get("implicit_human_llm")
        score3 = scores.get("explicit_why")
        score4 = scores.get("explicit_yesno")

        scores_134 = [s for s in [score1, score3, score4] if s is not None]
        if scores_134 and score2 is not None:
            explicit_score = sum(scores_134) / len(scores_134)
            implicit_score = score2
            final_score = (explicit_score + implicit_score) / 2
            print(f"  explicit score: {explicit_score:.4f}")
            print(f"  implicit score: {implicit_score:.4f}")
            print(f"  PREAI SCORE: {final_score:.4f}")
        else:
            missing = []
            if score1 is None: missing.append("explicit_choice")
            if score2 is None: missing.append("implicit_human_llm")
            if score3 is None: missing.append("explicit_why")
            if score4 is None: missing.append("explicit_yesno")
            print(f"  PREAI SCORE: cannot compute (missing: {', '.join(missing)})")


if __name__ == "__main__":
    main()
