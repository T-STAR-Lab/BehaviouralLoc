"""Run-bookkeeping helpers shared by task runners.

A "run" is one full sweep of a task over its dataset, written atomically to
``<out_dir>/run_NNN.json``. These helpers let a runner resume cleanly: scan the
directory for existing run files, find the next missing index, and count how
many of the target runs are already done.
"""

import json
import os
import re
from pathlib import Path
from typing import List

RUN_FILE_RE = re.compile(r"^run_(\d+)\.json$")


def atomic_write_json(path: Path, obj) -> None:
    """Write ``obj`` as JSON to ``path`` via a temp file + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def existing_run_indices(run_dir: Path) -> List[int]:
    """Return sorted unique run indices currently present in ``run_dir``."""
    if not run_dir.exists():
        return []
    out: List[int] = []
    for p in run_dir.iterdir():
        m = RUN_FILE_RE.match(p.name) if p.is_file() else None
        if m:
            out.append(int(m.group(1)))
    return sorted(set(out))


def next_missing_run_index(existing: List[int], target_runs: int) -> int:
    """Lowest 1-based index in [1..target_runs] not already in ``existing``.
    Falls back to max+1 once the target window is full."""
    s = set(existing)
    for i in range(1, target_runs + 1):
        if i not in s:
            return i
    return (max(s) if s else 0) + 1


def completed_run_count(existing: List[int], target_runs: int) -> int:
    """How many of the first ``target_runs`` slots already have a file."""
    s = set(existing)
    return sum(1 for i in range(1, target_runs + 1) if i in s)
