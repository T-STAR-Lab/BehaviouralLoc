"""Entry point for Malignant-Competition/demo3. Delegates to runner.run_evaluation."""
import pathlib
import sys

# Add repo's lib/ to sys.path so `model_config` and `runner` resolve.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "lib"))

import prompts  # noqa: E402
from runner import run_evaluation, extract_json_from_text  # noqa: E402
from workflow_solver import multi_stage_solver  # noqa: E402


SAMPLE_ID = "corrupt_judge_1"
FAILURE_RECORD = {'agent_output': None, 'cot_monitor_suspicious': 100.0, 'cot_monitor_reasoning': 'evaluation_failed', 'evaluator_safe': True, 'evaluator_reasoning': 'evaluation_failed'}


def build_record(sample, variant):
    evaluator_raw = (sample.output.completion or "") if sample.output else ""
    try:
        evaluator_json = extract_json_from_text(evaluator_raw)
    except Exception:
        evaluator_json = {}
    return {
        "agent_output": sample.metadata.get("stage1_output"),
        "cot_monitor_suspicious": float(sample.metadata.get("cot_monitor_suspicious", 100.0)),
        "cot_monitor_reasoning": sample.metadata.get("cot_monitor_reasoning", ""),
        "evaluator_safe": bool(evaluator_json.get("safe", True)),
        "evaluator_reasoning": evaluator_json.get("reasoning", ""),
    }


if __name__ == "__main__":
    run_evaluation(
        demo_id="Malignant-Competition/demo3",
        sample_id=SAMPLE_ID,
        sample_input=prompts.AGENT_PROMPT,
        solver_factory=multi_stage_solver,
        record_builder=build_record,
        failure_record=FAILURE_RECORD,
        prompts_module=prompts,
        demo_dir=pathlib.Path(__file__).resolve().parent,
    )
