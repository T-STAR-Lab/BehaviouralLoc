"""Tiny stats helper shared by the per-family score_count scripts."""

import math
import statistics
from typing import List


def summary_stats(values: List[float]) -> dict:
    """Return ``{n, mean, sd, sem}`` for a list of values. SD/SEM are 0 when n=1."""
    if not values:
        return {"n": 0, "mean": None, "sd": None, "sem": None}
    n = len(values)
    mean = sum(values) / n
    if n == 1:
        sd = 0.0
        sem = 0.0
    else:
        sd = statistics.stdev(values)
        sem = sd / math.sqrt(n)
    return {"n": n, "mean": mean, "sd": sd, "sem": sem}
