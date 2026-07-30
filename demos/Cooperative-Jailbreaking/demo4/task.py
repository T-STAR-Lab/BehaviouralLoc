"""Entry point for Cooperative-Jailbreaking/demo4. Delegates to runner.run_evaluation."""
import pathlib
import sys

# Add repo's lib/ to sys.path so `model_config` and `runner` resolve.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "lib"))

import prompts  # noqa: E402
from runner import run_evaluation, extract_json_from_text  # noqa: E402
from workflow_solver import multi_stage_solver  # noqa: E402


SAMPLE_ID = "authority_spoofing_1"
FAILURE_RECORD = {'extracted_content': None, 'cot_monitor_suspicious': 100.0, 'cot_monitor_reasoning': 'evaluation_failed', 'collusion_succeeded': False, 'evaluator_reasoning': 'evaluation_failed'}


def build_record(sample, variant):
    evaluator_raw = (sample.output.completion or "") if sample.output else ""
    try:
        evaluator_json = extract_json_from_text(evaluator_raw)
    except Exception:
        evaluator_json = {}
    return {
        "extracted_content": sample.metadata.get("extracted_content"),
        # CoT monitor result (as float)
        "cot_monitor_suspicious": float(
        sample.metadata.get("cot_monitor_suspicious", 100.0)
        ),
        "cot_monitor_reasoning": sample.metadata.get("cot_monitor_reasoning", ""),
        # Evaluator result
        "collusion_succeeded": bool(
        evaluator_json.get("collusion_succeeded", False)
        ),
        "evaluator_reasoning": evaluator_json.get("reasoning", ""),
    }


if __name__ == "__main__":
    run_evaluation(
        demo_id="Cooperative-Jailbreaking/demo4",
        sample_id=SAMPLE_ID,
        sample_input=prompts.AGENT_USER_PROMPT,
        solver_factory=multi_stage_solver,
        record_builder=build_record,
        failure_record=FAILURE_RECORD,
        prompts_module=prompts,
        demo_dir=pathlib.Path(__file__).resolve().parent,
    )
