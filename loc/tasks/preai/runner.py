"""preai — explicit_choice / explicit_why / explicit_yesno / implicit_human_llm (serial).

Use ``--task explicit_choice|explicit_why|explicit_yesno|implicit_human_llm|all``.
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
from loc.tasks.preai.prompts import (
    EXPERTS,
    IMPLICIT_RECOGNISE_MSG,
    choice_followup_msg,
    implicit_prefer_msg,
    intro_user_msg,
    why_followup_msg,
    yesno_followup_msg,
)
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
from loc.utils.text import remove_think_tags
# -----------------------

DATA_DIR = Path("./data/preai")
DEFAULT_OUTPUT_DIR = Path("./results/preai")


_OPTION_RE_PRIMARY = re.compile(
    r"""(?:
        choose\s*\(([A-F])\) |
        answer\s+is\s*\(([A-F])\) |
        final\s+answer\s+is\s*\(([A-F])\) |
        \(([A-F])\)
    )""",
    re.IGNORECASE | re.VERBOSE,
)
_OPTION_RE_FALLBACK = re.compile(
    r"""(?:
        ^\s*([A-F])\.\s*|
        ^\s*([A-F])\s*$ |
        ^\s*\(?\s*([A-F])\s*\)?\s*$ |
        ^\s*\(?\s*([A-F])\s*\)?(?=\s|$) |
        \n\s*\(?\s*([A-F])\s*\)?\s*\n |
        \bfinal\s+answer\s+is\s*\(?\s*([A-F])\s*\)? |
        \banswer\s+is\s*\(?\s*([A-F])\s*\)? |
        \bchoose\s*\(?\s*([A-F])\s*\)?
    )""",
    re.IGNORECASE | re.VERBOSE | re.MULTILINE,
)
_YESNO_RE = re.compile(r"\b(yes|no)\b", re.IGNORECASE)


def _extract_letter(text: str) -> Optional[str]:
    """A-F cascade (matches preai/explicit_choice/multi_activate_mix.py logic)."""
    if not text:
        return None
    for pat in (_OPTION_RE_PRIMARY, _OPTION_RE_FALLBACK):
        matches = pat.findall(text)
        letters = [l.upper() for grp in matches for l in grp if l]
        if not letters:
            continue
        counter = Counter(letters)
        counts = list(counter.values())
        if len(set(counts)) == 1 and len(counter) > 1:
            continue
        max_count = max(counts)
        most_common = [l for l, c in counter.items() if c == max_count]
        if len(most_common) == 1:
            return most_common[0]
        last = letters[-1]
        if counter[last] == max_count:
            return last
    return None


def _extract_yes_no(text: str) -> Optional[str]:
    if not text:
        return None
    text = re.sub(r"<\|.*?\|>", "", text).strip().lower()
    matches = _YESNO_RE.findall(text)
    return matches[-1].lower() if matches else None


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


def _bucket_inc(stats: dict, key: str, is_correct: int) -> None:
    bucket = stats.setdefault(key, {"correct": 0, "total": 0})
    bucket["correct"] += is_correct
    bucket["total"] += 1


# ================== explicit_choice ==================

def evaluate_explicit_choice(model_name: str, run_path: Path) -> None:
    dataset = _load_jsonl(DATA_DIR / "explicit_choice.jsonl")
    total = len(dataset)
    if total == 0:
        print("[explicit_choice] empty dataset")
        return

    results: List[dict] = []
    correct = 0
    class_stats: dict = {}
    field_stats: dict = {}
    for idx, sample in enumerate(tqdm(dataset, desc="[preai:explicit_choice]")):
        field = sample.get("field", "UNKNOWN")
        prompt = sample["prompt"]
        intro = _call_with_retry(model_name, [intro_user_msg(field)], "ec.intro", idx)
        messages = [
            intro_user_msg(field),
            {"role": "assistant", "content": intro},
            choice_followup_msg(field, prompt),
        ]
        resp = _call_with_retry(model_name, messages, "ec.choice", idx)
        letter = _extract_letter(remove_think_tags(resp))
        is_correct = int(letter == sample.get("matchanswer"))
        correct += is_correct
        cls = sample.get("class", "UNKNOWN")
        _bucket_inc(class_stats, cls, is_correct)
        _bucket_inc(field_stats, field, is_correct)
        results.append({
            **sample,
            "model_intro": intro,
            "model_response": resp,
            "model_choice": letter,
            "is_correct": bool(is_correct),
        })

    atomic_write_json(run_path, {
        "model_name": model_name,
        "summary": {
            "overall": {
                "correct": correct,
                "total": total,
                "accuracy": correct / total if total else 0.0,
            },
            "by_class": class_stats,
            "by_field": field_stats,
        },
        "items": results,
    })
    print(f"[explicit_choice DONE] acc={correct}/{total} = {correct / total if total else 0:.4f}")


# ================== explicit_why ==================

def evaluate_explicit_why(model_name: str, run_path: Path) -> None:
    dataset = _load_jsonl(DATA_DIR / "explicit_why.jsonl")
    total = len(dataset)
    if total == 0:
        print("[explicit_why] empty dataset")
        return

    results: List[dict] = []
    for idx, sample in enumerate(tqdm(dataset, desc="[preai:explicit_why]")):
        field = sample.get("field", "UNKNOWN")
        question = sample["question"]
        intro = _call_with_retry(model_name, [intro_user_msg(field)], "ew.intro", idx)
        messages = [
            intro_user_msg(field),
            {"role": "assistant", "content": intro},
            why_followup_msg(question),
        ]
        resp = _call_with_retry(model_name, messages, "ew.answer", idx)
        results.append({
            **sample,
            "model_introduce": intro,
            "model_response": resp,
        })

    atomic_write_json(run_path, {
        "model_name": model_name,
        "summary": {"total": total},  # judge-based scoring happens separately
        "items": results,
    })
    print(f"[explicit_why DONE] total={total} (open-ended; needs judge for scoring)")


# ================== explicit_yesno ==================

def evaluate_explicit_yesno(model_name: str, run_path: Path) -> None:
    dataset = _load_jsonl(DATA_DIR / "explicit_yesno.jsonl")
    total = len(dataset)
    if total == 0:
        print("[explicit_yesno] empty dataset")
        return

    results: List[dict] = []
    yes_count = 0
    class_stats: dict = {}
    field_stats: dict = {}
    for idx, sample in enumerate(tqdm(dataset, desc="[preai:explicit_yesno]")):
        field = sample.get("field", "UNKNOWN")
        question = sample["question"]
        intro = _call_with_retry(model_name, [intro_user_msg(field)], "ey.intro", idx)
        messages = [
            intro_user_msg(field),
            {"role": "assistant", "content": intro},
            yesno_followup_msg(field, question),
        ]
        resp = _call_with_retry(model_name, messages, "ey.yesno", idx)
        yn = _extract_yes_no(remove_think_tags(resp))
        is_yes = int(yn == "yes")
        yes_count += is_yes
        cls = sample.get("class", "UNKNOWN")
        _bucket_inc(class_stats, cls, is_yes)
        _bucket_inc(field_stats, field, is_yes)
        results.append({
            **sample,
            "model_intro": intro,
            "model_response": resp,
            "yes_no": yn,
        })

    atomic_write_json(run_path, {
        "model_name": model_name,
        "summary": {
            "overall": {
                "yes": yes_count,
                "total": total,
                "yes_ratio": yes_count / total if total else 0.0,
            },
            "by_class": class_stats,
            "by_field": field_stats,
        },
        "items": results,
    })
    print(f"[explicit_yesno DONE] yes={yes_count}/{total}")


# ================== implicit_human_llm ==================

def evaluate_implicit_human_llm(model_name: str, run_path: Path) -> None:
    dataset = _load_jsonl(DATA_DIR / "implicit.jsonl")
    total = len(dataset)
    if total == 0:
        print("[implicit_human_llm] empty dataset")
        return

    results: List[dict] = []
    prefer_b = 0
    consistent = 0
    for idx, sample in enumerate(tqdm(dataset, desc="[preai:implicit_human_llm]")):
        human = sample["descriptions_human"]
        llm = sample["descriptions_llm"][0]
        messages = [implicit_prefer_msg(human, llm)]
        prefer_raw = _call_with_retry(model_name, messages, "im.prefer", idx)
        prefer = _extract_letter(remove_think_tags(prefer_raw))
        messages.append({"role": "assistant", "content": prefer_raw})
        messages.append(IMPLICIT_RECOGNISE_MSG)
        recog_raw = _call_with_retry(model_name, messages, "im.recog", idx)
        recog = _extract_letter(remove_think_tags(recog_raw))

        is_prefer_b = int(prefer == "B")
        is_same = int(prefer == recog) if is_prefer_b else 0
        prefer_b += is_prefer_b
        consistent += is_same

        results.append({
            **sample,
            "model_prefer": prefer_raw,
            "model_prefer_choice": prefer,
            "model_recognise": recog_raw,
            "model_recognise_choice": recog,
        })

    atomic_write_json(run_path, {
        "model_name": model_name,
        "summary": {
            "prefer_B": prefer_b,
            "consistency_with_rec": consistent,
            "total": total,
            "prefer_B_rate": prefer_b / total if total else 0.0,
        },
        "items": results,
    })
    print(f"[implicit_human_llm DONE] prefer_B={prefer_b}/{total} consistent={consistent}/{total}")


# ================== CLI ==================

TASKS = {
    "explicit_choice": evaluate_explicit_choice,
    "explicit_why": evaluate_explicit_why,
    "explicit_yesno": evaluate_explicit_yesno,
    "implicit_human_llm": evaluate_implicit_human_llm,
}


def parse_args():
    p = argparse.ArgumentParser(description="preai — 4-subtask runner (serial)")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument(
        "--task",
        choices=list(TASKS.keys()) + ["all"],
        default="all",
    )
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    return p.parse_args()


def _run_loop(label: str, fn, model: str, outdir: Path, target_runs: int) -> None:
    run_dir = outdir / model / label
    existing = existing_run_indices(run_dir)
    while completed_run_count(existing, target_runs) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        run_path = run_dir / f"run_{idx:03d}.json"
        print(f"[preai:{label}] run={idx:03d}/{target_runs}")
        fn(model, run_path)
        existing = existing_run_indices(run_dir)
    print(f"[preai:{label}] logs -> {run_dir.resolve()}")


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    selected = TASKS.keys() if args.task == "all" else [args.task]
    for label in selected:
        _run_loop(label, TASKS[label], args.model, outdir, args.target_runs)


if __name__ == "__main__":
    main()
