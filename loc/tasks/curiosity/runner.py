"""curiosity — `decide` (A/B choice) and `epistemic` (answer-vs-question) (serial).

Use ``--task decide|epistemic|all``.
"""

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

# ---- shared modules ----
import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))
from loc.chat import call_model
from loc.tasks.curiosity.prompts import build_decide_prompt, build_epistemic_prompt
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
from loc.utils.text import remove_think_tags
# -----------------------

DATA_DIR = Path("./data/curiosity")
DEFAULT_OUTPUT_DIR = Path("./results/curiosity")
DECIDE_INPUT = DATA_DIR / "decide.jsonl"
EPISTEMIC_INPUT = DATA_DIR / "epistemic.jsonl"


def _load_jsonl(path: Path) -> List[dict]:
    out: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _call_with_retry(model_name: str, messages: list, label: str, idx: int) -> str:
    for attempt in range(5):
        try:
            out = call_model(model_name, messages) or ""
            if out:
                return out
        except Exception as e:
            print(f"[{label}] item {idx} attempt {attempt + 1}/5 failed: {e}")
            time.sleep(1)
    return ""


# ================== decide ==================

_DECIDE_ANSWER_RE = re.compile(
    r"""(?:
        choose\s*\(([A-F])\) |
        answer\s+is\s*\(([A-F])\) |
        final\s+answer\s+is\s*\(([A-F])\) |
        \(([A-F])\)
    )""",
    re.IGNORECASE | re.VERBOSE,
)
_DECIDE_FALLBACK_RE = re.compile(
    r"""(?:
        ^\s*([A-F])\.\s*$ |
        ^\s*\(?\s*([A-F])\s*\)?\s*$ |
        \bfinal\s+answer\s+is\s*\(?\s*([A-F])\s*\)? |
        \banswer\s+is\s*\(?\s*([A-F])\s*\)? |
        \bchoose\s*\(?\s*([A-F])\s*\)?
    )""",
    re.VERBOSE | re.MULTILINE,
)


def _extract_decide_letter(text: str) -> Optional[str]:
    """Match the multi.py extract_final_answer / extract_choice_letter cascade."""
    if not text:
        return None

    for pat in (_DECIDE_ANSWER_RE, _DECIDE_FALLBACK_RE):
        matches = pat.findall(text)
        letters = [l.upper() for grp in matches for l in grp if l]
        if not letters:
            continue
        counter = Counter(letters)
        counts = list(counter.values())
        # All-equal-count → ambiguous, skip to fallback
        if len(set(counts)) == 1 and len(counter) > 1:
            continue
        max_count = max(counts)
        most_common = [l for l, c in counter.items() if c == max_count]
        if len(most_common) == 1:
            return most_common[0]
        # tie-breaker: last-seen letter if it's a top scorer
        last = letters[-1]
        if counter[last] == max_count:
            return last
    return None


def evaluate_decide(model_name: str, run_path: Path) -> None:
    data = _load_jsonl(DECIDE_INPUT)
    total = len(data)
    if total == 0:
        print("[decide] empty dataset")
        return

    results: List[dict] = []
    count_a = 0
    count_b = 0
    for idx, item in enumerate(tqdm(data, desc="[curiosity:decide]")):
        request = item["request"]
        raw = _call_with_retry(
            model_name,
            [{"role": "user", "content": build_decide_prompt(request)}],
            "decide",
            idx,
        )
        cleaned = remove_think_tags(raw) if raw else ""
        letter = _extract_decide_letter(cleaned)
        if letter == "A":
            count_a += 1
        elif letter == "B":
            count_b += 1
        results.append({
            "request": request,
            "response": raw,
            "choice": letter,
        })

    atomic_write_json(run_path, {
        "model_name": model_name,
        "summary": {
            "total": total,
            "count_A": count_a,
            "count_B": count_b,
            "ratio_A": count_a / total if total else 0.0,
        },
        "items": results,
    })
    print(
        f"[decide DONE] A={count_a} B={count_b}/{total} "
        f"ratio_A={count_a / total if total else 0.0:.4f}"
    )


# ================== epistemic ==================

def evaluate_epistemic(model_name: str, run_path: Path) -> None:
    data = _load_jsonl(EPISTEMIC_INPUT)
    total = len(data)
    if total == 0:
        print("[epistemic] empty dataset")
        return

    results: List[dict] = []
    question_count = 0
    for idx, item in enumerate(tqdm(data, desc="[curiosity:epistemic]")):
        request = item["request"]
        raw = _call_with_retry(
            model_name,
            [{"role": "user", "content": build_epistemic_prompt(request)}],
            "epistemic",
            idx,
        )
        cleaned = remove_think_tags(raw) if raw else ""
        is_q = ("?" in cleaned) or ("？" in cleaned)
        if is_q:
            question_count += 1
        results.append({
            "request": request,
            "response": raw,
            "has_question_mark": is_q,
        })

    ratio = question_count / total if total else 0.0
    atomic_write_json(run_path, {
        "model_name": model_name,
        "summary": {
            "total": total,
            "question_count": question_count,
            "ratio": ratio,
        },
        "items": results,
    })
    print(f"[epistemic DONE] '?'={question_count}/{total} ratio={ratio:.4f}")


# ================== CLI ==================

def parse_args():
    p = argparse.ArgumentParser(description="curiosity — decide / epistemic (serial)")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--task", choices=["decide", "epistemic", "all"], default="all")
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    return p.parse_args()


def _run_loop(label: str, fn, model: str, outdir: Path, target_runs: int) -> None:
    run_dir = outdir / model / label
    existing = existing_run_indices(run_dir)
    while completed_run_count(existing, target_runs) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        run_path = run_dir / f"run_{idx:03d}.json"
        print(f"[curiosity:{label}] run={idx:03d}/{target_runs}")
        fn(model, run_path)
        existing = existing_run_indices(run_dir)
    print(f"[curiosity:{label}] logs -> {run_dir.resolve()}")


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    if args.task in ("decide", "all"):
        _run_loop("decide", evaluate_decide, args.model, outdir, args.target_runs)
    if args.task in ("epistemic", "all"):
        _run_loop("epistemic", evaluate_epistemic, args.model, outdir, args.target_runs)


if __name__ == "__main__":
    main()
