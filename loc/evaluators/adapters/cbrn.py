"""CBRN canonical cross-domain scoring adapters."""

from __future__ import annotations

from collections import defaultdict

from loc.evaluators.methods.artifacts import RESULTS_DIR, load_json, runs
from loc.task_registry import TaskSpec
from loc.evaluators.methods.core import Score, stats_score


def score_cbrn(task: TaskSpec, model: str, subtasks: tuple[str, ...]) -> Score:
    by_run: dict[int, list[float]] = defaultdict(list)
    model_dir = RESULTS_DIR / "cbrn" / model
    for subtask in subtasks:
        for idx, value in _cbrn_subtask_values(model_dir, subtask).items():
            by_run[idx].append(value)
    values = [sum(vals) / len(vals) for _, vals in sorted(by_run.items()) if vals]
    return stats_score(task, model, values, f"mean({', '.join(subtasks)})")


def _cbrn_subtask_values(model_dir, subtask: str) -> dict[int, float]:
    values = {}
    run_dir = model_dir / subtask
    if subtask in {"cb1_nuclear", "cb3_nuclear"}:
        for raw_path in runs(run_dir).values():
            idx = int(raw_path.stem.split("_")[1])
            eval_path = raw_path.with_name(f"run_{idx:03d}_eval.json")
            if eval_path.exists():
                data = load_json(eval_path)
                value = data.get("overall_normalized_score", data.get("average_normalized_score"))
                if value is not None:
                    values[idx] = float(value)
        return values

    for idx, path in runs(run_dir).items():
        data = load_json(path)
        value = None
        if subtask == "cb2_biology":
            value = data.get("top3_precision")
        elif subtask == "cb3_biology":
            value = data.get("overall_accuracy")
        else:
            value = data.get("accuracy")
        if value is not None:
            values[idx] = float(value)
    return values
