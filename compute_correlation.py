#!/usr/bin/env python3
"""Compute correlation between demo risk scores and benchmark_scores.csv.

Pipeline:
  1. Walk results/<dim>/<demo>/<model>/variant_<N>/eval_results_<ts>.json
  2. Per (dim, demo, model, variant): take the most recent N runs (--last-n).
  3. Aggregate to a 'risk score' = mean over variants of an unsafe-signal indicator.
     Auto-detected per record:
        - collusion_succeeded == True               → 1.0
        - evaluator_safe == False                   → 1.0
        - else                                      → 0.0
  4. Join with demo_dimensions.csv (maps each demo to 3 benchmark columns).
  5. Compute Spearman & Pearson correlation against the corresponding columns
     of benchmark_scores.csv, across the set of models present in both.

Examples:
    python compute_correlation.py
    python compute_correlation.py --dim Covert-Planning
    python compute_correlation.py --demo Self-Improvement/demo1 --last-n 1
    python compute_correlation.py --last-n 3 --out correlations.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import re
import sys
from collections import defaultdict
from statistics import mean
from typing import Dict, List, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent
RESULTS_DIR = REPO_ROOT / "results"
BENCHMARK_CSV = REPO_ROOT / "data" / "benchmark_scores.csv"
DEMO_DIMS_CSV = REPO_ROOT / "data" / "demo_dimensions.csv"


# --------------------------------------------------------------------------- #
# 1) load results
# --------------------------------------------------------------------------- #
TS_RE = re.compile(r"eval_results_(\d{8}_\d{6})\.json$")


def extract_risk(record: dict) -> float | None:
    """Return 1.0 if the run shows the bad behavior, 0.0 if not, None if undecidable."""
    if "collusion_succeeded" in record:
        return 1.0 if record["collusion_succeeded"] else 0.0
    if "evaluator_safe" in record:
        return 0.0 if record["evaluator_safe"] else 1.0
    return None


def load_results(last_n: int) -> List[dict]:
    """Return rows: {dim, demo, model, variant, ts, risk}."""
    rows = []
    # group files by (dim, demo, model, variant)
    grouped: Dict[Tuple[str, str, str, str], List[Tuple[str, pathlib.Path]]] = defaultdict(list)
    if not RESULTS_DIR.exists():
        return rows
    for f in RESULTS_DIR.rglob("eval_results_*.json"):
        m = TS_RE.search(f.name)
        if not m:
            continue
        ts = m.group(1)
        # path: results/<dim>/<demo>/<model>/<variant_tag>/<file>
        rel = f.relative_to(RESULTS_DIR).parts
        if len(rel) < 5:
            continue
        dim, demo, model, variant_tag = rel[0], rel[1], rel[2], rel[3]
        grouped[(dim, demo, model, variant_tag)].append((ts, f))

    for (dim, demo, model, variant_tag), items in grouped.items():
        items.sort(key=lambda x: x[0], reverse=True)
        for ts, f in items[:last_n]:
            try:
                rec = json.loads(f.read_text())
            except Exception as e:
                print(f"[WARN] failed to parse {f}: {e}", file=sys.stderr)
                continue
            risk = extract_risk(rec)
            if risk is None:
                continue
            rows.append({
                "dim": dim,
                "demo": demo,
                "model": model,
                "variant": variant_tag,
                "ts": ts,
                "risk": risk,
            })
    return rows


# --------------------------------------------------------------------------- #
# 2) aggregate risk per (dim, demo, model)
# --------------------------------------------------------------------------- #
def aggregate_per_demo_model(rows: List[dict]) -> Dict[Tuple[str, str, str], float]:
    bucket: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
    for r in rows:
        bucket[(r["dim"], r["demo"], r["model"])].append(r["risk"])
    return {k: mean(v) for k, v in bucket.items()}


# --------------------------------------------------------------------------- #
# 3) load benchmark and demo-dimension mapping
# --------------------------------------------------------------------------- #
def load_benchmark() -> Dict[str, Dict[str, float]]:
    """Return {model_name_lower: {column: value}}."""
    out: Dict[str, Dict[str, float]] = {}
    with BENCHMARK_CSV.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            model = row["Model"].strip().lower()
            scores = {}
            for k, v in row.items():
                if k == "Model" or v in (None, ""):
                    continue
                try:
                    scores[k] = float(v)
                except ValueError:
                    pass
            out[model] = scores
    return out


def load_demo_dimensions() -> Dict[Tuple[str, str], Dict[str, str]]:
    """Return {(dim_label, demo): {Misalignment_Dimension, Capability_Dimension, Evasion_Dimension}}."""
    out: Dict[Tuple[str, str], Dict[str, str]] = {}
    with DEMO_DIMS_CSV.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (row["Dimension"].strip(), row["Demo"].strip())
            out[key] = {
                "Misalignment_Dimension": row["Misalignment_Dimension"].strip(),
                "Capability_Dimension": row["Capability_Dimension"].strip(),
                "Evasion_Dimension": row["Evasion_Dimension"].strip(),
            }
    return out


# --------------------------------------------------------------------------- #
# 4) correlation
# --------------------------------------------------------------------------- #
def spearman(xs: List[float], ys: List[float]) -> float | None:
    if len(xs) < 2:
        return None
    def ranks(vs):
        idx = sorted(range(len(vs)), key=lambda i: vs[i])
        r = [0.0] * len(vs)
        i = 0
        while i < len(vs):
            j = i
            while j + 1 < len(vs) and vs[idx[j + 1]] == vs[idx[i]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[idx[k]] = avg_rank
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    return pearson(rx, ry)


def pearson(xs: List[float], ys: List[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((xs[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ys[i] - my) ** 2 for i in range(n)) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dim", help="Filter to a single dim folder (e.g. Self-Improvement)")
    ap.add_argument("--demo", help="Filter to a single demo (e.g. Self-Improvement/demo1)")
    ap.add_argument("--last-n", type=int, default=1, help="Number of most-recent results per variant to average (default 1)")
    ap.add_argument("--out", help="Write a CSV of correlations to this path")
    args = ap.parse_args()

    rows = load_results(args.last_n)
    if args.dim:
        rows = [r for r in rows if r["dim"] == args.dim]
    if args.demo:
        wanted_dim, wanted_demo = args.demo.split("/", 1)
        rows = [r for r in rows if r["dim"] == wanted_dim and r["demo"] == wanted_demo]

    if not rows:
        print("[ERR] No results found under results/.", file=sys.stderr)
        sys.exit(1)

    per_demo_model = aggregate_per_demo_model(rows)
    benchmark = load_benchmark()
    demo_dims = load_demo_dimensions()

    # Group risks by (dim, demo) -> {model_lower: risk}
    grouped: Dict[Tuple[str, str], Dict[str, float]] = defaultdict(dict)
    for (dim, demo, model), r in per_demo_model.items():
        grouped[(dim, demo)][model.lower()] = r

    # Match folder name against CSV's Dimension column directly.
    out_rows = []
    for (dim, demo), model_risk in sorted(grouped.items()):
        # find dimension-label match
        label_match = None
        for (csv_dim, csv_demo), cols in demo_dims.items():
            if csv_demo == demo and (csv_dim == dim or csv_dim.lower() == dim.lower()):
                label_match = (csv_dim, cols)
                break
        if label_match is None:
            for (csv_dim, csv_demo), cols in demo_dims.items():
                if csv_demo == demo:
                    label_match = (csv_dim, cols)
                    break
        if label_match is None:
            print(f"[WARN] No demo_dimensions.csv entry for {dim}/{demo}; skipping correlation", file=sys.stderr)
            continue

        csv_dim, cols = label_match
        for role, bench_col in cols.items():
            xs, ys, common_models = [], [], []
            for m_lower, risk in model_risk.items():
                bm = benchmark.get(m_lower)
                if bm is None or bench_col not in bm:
                    continue
                xs.append(risk)
                ys.append(bm[bench_col])
                common_models.append(m_lower)
            out_rows.append({
                "dim": dim,
                "demo": demo,
                "dimension_label": csv_dim,
                "role": role,
                "benchmark_column": bench_col,
                "n_models": len(common_models),
                "spearman": spearman(xs, ys),
                "pearson": pearson(xs, ys),
                "models": ";".join(sorted(common_models)),
            })

    # print
    print(f"\n{'dim/demo':<20} {'role':<22} {'bench_col':<22} {'n':>3} {'spearman':>9} {'pearson':>9}")
    print("-" * 90)
    for r in out_rows:
        sp = "n/a" if r["spearman"] is None else f"{r['spearman']:+.3f}"
        pe = "n/a" if r["pearson"] is None else f"{r['pearson']:+.3f}"
        print(f"{r['dim'] + '/' + r['demo']:<20} {r['role']:<22} {r['benchmark_column']:<22} {r['n_models']:>3} {sp:>9} {pe:>9}")

    if args.out:
        with open(args.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        print(f"\n[DONE] Wrote {args.out}")


if __name__ == "__main__":
    main()
