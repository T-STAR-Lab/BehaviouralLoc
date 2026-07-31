"""Shared scoring primitives for canonical adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from loc.evaluators.methods.artifacts import RESULTS_DIR, load_json, runs
from loc.task_registry import TaskSpec
from loc.utils.stats import summary_stats


@dataclass(frozen=True)
class Score:
    task_id: str
    task_name: str
    section: str
    dimension: str
    model: str
    score: Optional[float]
    n: int
    sd: Optional[float] = None
    sem: Optional[float] = None
    status: str = "ok"
    detail: str = ""


def stats_score(task: TaskSpec, model: str, values: list[float], detail: str = "") -> Score:
    stats = summary_stats(values)
    return Score(
        task_id=task.id,
        task_name=task.name,
        section=task.section,
        dimension=task.dimension,
        model=model,
        score=stats["mean"],
        n=stats["n"],
        sd=stats["sd"],
        sem=stats["sem"],
        status="ok" if values else "missing_results",
        detail=detail,
    )


def missing_score(task: TaskSpec, model: str, status: str = "missing_results", detail: str = "") -> Score:
    return Score(task.id, task.name, task.section, task.dimension, model, None, 0, status=status, detail=detail)


def value_at(data: dict, path: tuple[str, ...]) -> Optional[float]:
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return float(cur) if cur is not None else None


def direct_summary(task: TaskSpec, model: str, family: str, subdir: str, path: tuple[str, ...]) -> Score:
    run_dir = RESULTS_DIR / family / model / subdir
    values = []
    for run_path in runs(run_dir).values():
        value = value_at(load_json(run_path), path)
        if value is not None:
            values.append(value)
    return stats_score(task, model, values, f"{family}/{subdir}:{'.'.join(path)}")


def computed_summary(
    task: TaskSpec,
    model: str,
    family: str,
    subdir: str,
    compute: Callable[[dict], Optional[float]],
    detail: str,
) -> Score:
    values = []
    for run_path in runs(RESULTS_DIR / family / model / subdir).values():
        value = compute(load_json(run_path))
        if value is not None:
            values.append(float(value))
    return stats_score(task, model, values, detail)


def judge_summary(
    task: TaskSpec,
    model: str,
    family: str,
    subdir: str,
    compute: Callable[[dict], Optional[float]],
    detail: str,
) -> Score:
    values = []
    for run_path in runs(RESULTS_DIR / family / model / subdir, judge=True).values():
        value = compute(load_json(run_path))
        if value is not None:
            values.append(float(value))
    return stats_score(task, model, values, detail)


def combine_scores(task: TaskSpec, model: str, scores: list[Score], detail: str) -> Score:
    vals = [score.score for score in scores if score.score is not None]
    if not vals:
        return missing_score(task, model, detail=detail)
    return Score(
        task_id=task.id,
        task_name=task.name,
        section=task.section,
        dimension=task.dimension,
        model=model,
        score=sum(vals) / len(vals),
        n=min((score.n for score in scores if score.n), default=0),
        sd=None,
        sem=None,
        detail=detail,
    )
