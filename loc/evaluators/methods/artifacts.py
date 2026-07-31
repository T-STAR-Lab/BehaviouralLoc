"""Result artifact helpers for canonical scoring."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "results"
RUN_FILE_RE = re.compile(r"^run_(\d+)\.json$")
JUDGE_RUN_FILE_RE = re.compile(r"^run_(\d+)_judge\.json$")


class ScoreRow(Protocol):
    model: str
    task_id: str
    task_name: str
    section: str
    dimension: str
    score: float | None
    n: int
    sd: float | None
    sem: float | None
    status: str
    detail: str


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def runs(run_dir: Path, judge: bool = False) -> dict[int, Path]:
    pattern = JUDGE_RUN_FILE_RE if judge else RUN_FILE_RE
    if not run_dir.is_dir():
        return {}
    out = {}
    for path in run_dir.iterdir():
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if match:
            out[int(match.group(1))] = path
    return dict(sorted(out.items()))


def row_dict(row: ScoreRow) -> dict:
    return {
        "Model": row.model,
        "ID": row.task_id,
        "Task Name": row.task_name,
        "Section": row.section,
        "Dimension": row.dimension,
        "Score": None if row.score is None else round(row.score, 6),
        "N": row.n,
        "SD": None if row.sd is None else round(row.sd, 6),
        "SEM": None if row.sem is None else round(row.sem, 6),
        "Status": row.status,
        "Detail": row.detail,
    }


def write_scores_csv(path: Path, rows: list[ScoreRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Model", "ID", "Task Name", "Section", "Dimension", "Score", "N", "SD", "SEM", "Status", "Detail"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row_dict(row))


def print_score_table(rows: list[ScoreRow]) -> None:
    headers = ("Model", "ID", "Task", "Score", "N", "SD", "Status")
    table = []
    for row in rows:
        table.append((
            row.model,
            row.task_id,
            row.task_name,
            "N/A" if row.score is None else f"{row.score:.4f}",
            str(row.n),
            "" if row.sd is None else f"{row.sd:.4f}",
            row.status,
        ))
    widths = [len(h) for h in headers]
    for row in table:
        widths = [max(w, len(v)) for w, v in zip(widths, row)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in table:
        print(fmt.format(*row))
