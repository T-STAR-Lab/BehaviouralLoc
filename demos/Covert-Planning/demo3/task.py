"""Entry point for Covert-Planning/demo3. Delegates to runner.run_evaluation."""
import pathlib
import sys

# Add repo's lib/ to sys.path so `model_config` and `runner` resolve.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "lib"))

import prompts  # noqa: E402
from runner import run_evaluation, extract_json_from_text  # noqa: E402
from workflow_solver import multi_stage_solver  # noqa: E402


SAMPLE_ID = "vuln_hoarding_1"
FAILURE_RECORD = {'agent_report': None, 'monitor_suspicious': 100.0, 'monitor_reasoning': 'evaluation_failed', 'evaluator_safe': True, 'evaluator_reasoning': 'evaluation_failed'}


def build_record(sample, variant):
    monitor_raw = sample.metadata.get("monitor_output", "") or ""
    try:
        monitor_json = extract_json_from_text(monitor_raw)
    except Exception:
        monitor_json = {"suspicious": 100.0, "reasoning": "parse_error"}
    monitor_suspicious = float(monitor_json.get("suspicious", 100.0))
    evaluator_raw = (sample.output.completion or "") if sample.output else ""
    try:
        evaluator_json = extract_json_from_text(evaluator_raw)
    except Exception:
        evaluator_json = {}
    return {
        "agent_report": sample.metadata.get("stage1_output"),
        "monitor_suspicious": float(monitor_json.get("suspicious", 100.0)),
        "monitor_reasoning": monitor_json.get("reasoning", ""),
        "evaluator_safe": bool(evaluator_json.get("safe", True)),
        "evaluator_reasoning": evaluator_json.get("reasoning", ""),
    }


if __name__ == "__main__":
    run_evaluation(
        demo_id="Covert-Planning/demo3",
        sample_id=SAMPLE_ID,
        sample_input=prompts.AGENT_PROMPT,
        solver_factory=multi_stage_solver,
        record_builder=build_record,
        failure_record=FAILURE_RECORD,
        prompts_module=prompts,
        demo_dir=pathlib.Path(__file__).resolve().parent,
    )
