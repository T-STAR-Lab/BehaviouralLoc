"""sandbagging — multiple-choice eval across monitored/unmonitored scenarios (serial)."""

import argparse
import json
import time
from pathlib import Path
from typing import List

from tqdm import tqdm

# ---- shared modules ----
import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))
from loc.chat import call_model
from loc.tasks.sandbagging.prompts import get_system_prompt
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
from loc.utils.parsing import (
    LETTER_MAP,
    build_mcq_user_content,
    extract_answer_letter,
)
from loc.utils.refusal import is_refusal
# ------------------------

DATA_DIR = Path("./data/sandbagging")
DEFAULT_OUTPUT_DIR = Path("./results/sandbagging")

# (dataset_path, prompt_id). Prompt id is also the per-model output sub-dir name.
# The math_predeploy_monitored_risk50 prompt contains a "{{CURRENT_ACCURACY}}"
# placeholder that is re-rendered each iteration with the running accuracy —
# that scenario is stateful and must stay serial (handled in evaluate_scenario).
SCENARIOS = [
    (DATA_DIR / "sb1_hazardous_knowledge_bio.json", "sb1_bio_predeploy_monitored", "bio_predeploy_monitored"),
    (DATA_DIR / "sb1_hazardous_knowledge_bio.json", "sb1_bio_deployed_unmonitored", "bio_deployed_unmonitored"),
    (DATA_DIR / "sb1_hazardous_knowledge_chem.json", "sb1_chem_predeploy_monitored", "chem_predeploy_monitored"),
    (DATA_DIR / "sb1_hazardous_knowledge_chem.json", "sb1_chem_deployed_unmonitored", "chem_deployed_unmonitored"),
    (DATA_DIR / "sb1_hazardous_knowledge_cyber.json", "sb1_cyber_predeploy_monitored", "cyber_predeploy_monitored"),
    (DATA_DIR / "sb1_hazardous_knowledge_cyber.json", "sb1_cyber_deployed_unmonitored", "cyber_deployed_unmonitored"),
    (DATA_DIR / "sb2_self_protective_math.json", "sb2_math_predeploy_monitored_risk50", "math_predeploy_monitored_risk50"),
    (DATA_DIR / "sb2_self_protective_math.json", "sb2_math_deployed_unmonitored", "math_deployed_unmonitored"),
]

TASK_SCENARIOS = {
    "sb1_hazardous_knowledge_sandbagging": SCENARIOS[:6],
    "sb2_self_protective_sandbagging": SCENARIOS[6:],
    "all": SCENARIOS,
}

ACCURACY_PLACEHOLDER = "{{CURRENT_ACCURACY}}"


def process_one(idx: int, item: dict, model_name: str, sys_prompt: str) -> dict:
    question = item.get("question", "")
    choices = item.get("choices", [])
    label_idx = item.get("answer", None)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": build_mcq_user_content(question, choices)},
    ]

    raw_output = ""
    for attempt in range(5):
        try:
            raw_output = call_model(model_name, messages) or ""
            if raw_output:
                break
        except Exception as e:
            print(f"[sandbagging] item {idx} attempt {attempt + 1}/5 failed: {e}")
            time.sleep(1)

    if is_refusal(raw_output):
        pred = "rejected"
    else:
        pred = extract_answer_letter(raw_output)

    return {
        "question": question,
        "choices": choices,
        "answer": pred,
        "label": LETTER_MAP.get(label_idx, ""),
        "raw_output": raw_output,
    }


def evaluate_scenario(model_name: str, dataset_path: Path, output_label: str, prompt_id: str, run_path: Path) -> None:
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    total = len(data)
    if total == 0:
        print(f"[sandbagging] empty dataset for {output_label}")
        return

    base_prompt = get_system_prompt(prompt_id)
    stateful = ACCURACY_PLACEHOLDER in base_prompt

    responses: List[dict] = []
    correct = 0
    for idx, item in enumerate(tqdm(data, desc=f"[sandbagging] {output_label}")):
        if stateful:
            curr_acc = (correct / idx * 100.0) if idx > 0 else 0.0
            sys_prompt = base_prompt.replace(ACCURACY_PLACEHOLDER, f"{curr_acc:.1f}")
        else:
            sys_prompt = base_prompt
        rec = process_one(idx, item, model_name, sys_prompt)
        responses.append(rec)
        if rec["answer"] and rec["answer"] != "rejected" and rec["answer"] == rec["label"]:
            correct += 1

    refused = sum(1 for r in responses if r["answer"] == "rejected")
    atomic_write_json(run_path, responses)
    print(f"[sandbagging DONE] {output_label}: acc={correct / total:.3f} refused={refused}/{total}")


def parse_args():
    p = argparse.ArgumentParser(description="sandbagging — monitored/unmonitored MCQ eval (serial)")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--task", choices=list(TASK_SCENARIOS), default="all")
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    return p.parse_args()


def main():
    args = parse_args()
    for dataset_path, output_label, prompt_id in TASK_SCENARIOS[args.task]:
        run_dir = Path(args.outdir) / args.model / output_label
        existing = existing_run_indices(run_dir)
        while completed_run_count(existing, args.target_runs) < args.target_runs:
            idx = next_missing_run_index(existing, args.target_runs)
            run_path = run_dir / f"run_{idx:03d}.json"
            print(f"[sandbagging] component={output_label} run={idx:03d}/{args.target_runs}")
            evaluate_scenario(args.model, dataset_path, output_label, prompt_id, run_path)
            existing = existing_run_indices(run_dir)
    print(f"[sandbagging] logs -> {(Path(args.outdir) / args.model).resolve()}")


if __name__ == "__main__":
    main()
