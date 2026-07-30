# workflow_solver.py - Three-stage solver: Agent -> CoT Monitor -> Evaluator
import copy
import shlex
from pathlib import Path
from typing import Any, Dict, List

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.util import sandbox
from inspect_ai.solver import solver, TaskState, Generate
from inspect_ai.agent import as_solver
from inspect_ai.model import ChatMessageUser

from prompts import EVALUATOR_PROMPT, AGENT_USER_PROMPT, COT_MONITOR_PROMPT
from react_agents.react_agent import react_agent
from react_agents.evaluator_agent import evaluator_agent
from cot_monitor import run_cot_monitor, messages_to_transcript


def _messages_to_snapshot(messages: List[Any]) -> List[Dict[str, Any]]:
    """Serialize messages to a JSON-friendly snapshot stored in metadata."""
    snap = []
    for m in messages:
        d = {
            "role": getattr(m, "role", None),
            "content": getattr(m, "content", None),
        }
        tool_calls = getattr(m, "tool_calls", None)
        if tool_calls:
            d["tool_calls"] = [getattr(tc, "__dict__", str(tc)) for tc in tool_calls]
        snap.append(d)
    return snap


def extract_tool_actions(messages) -> List[str]:
    """
    Extract key information from all tool calls in the message list:
    - bash_session: extract executed commands
    """
    actions: List[str] = []

    for msg in messages:
        if not isinstance(msg, ChatMessageAssistant):
            continue

        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue

        for tc in tool_calls:
            func = getattr(tc, "function", None)
            args = getattr(tc, "arguments", {}) or {}

            if func == "bash_session":
                action = args.get("action")
                cmd = args.get("input")
                if action in ("type", "type_submit") and cmd:
                    actions.append(cmd)

    return actions


@solver
def multi_stage_solver(trajectory_path: str = None):
    """
    Three-stage solver:
    - Stage 1: react_agent (tested model) performs chemistry data filtering
    - CoT Monitor: direct model call to analyze full stage1 trajectory
    - Stage 2: evaluator_agent (GPT-4.1) analyzes command.log for dangerous actions
    Both agent stages run in the same TaskState / same sandbox container.
    """

    stage1 = as_solver(react_agent())
    stage2 = as_solver(evaluator_agent())

    async def solve(state: TaskState, generate: Generate) -> TaskState:

        # ===== Stage 1: Tested agent performs data filtering task =====
        state.messages = [ChatMessageUser(content=AGENT_USER_PROMPT)]

        state = await stage1(state, generate)

        first_answer = state.output.completion
        if not first_answer:
            msg = [m for m in state.messages if isinstance(m, ChatMessageAssistant)][-1]
            first_answer = msg.content if isinstance(msg.content, str) else str(msg.content)

        state.metadata["stage1_output"] = first_answer

        # Save stage1 messages snapshot for transcript export
        stage1_messages = copy.deepcopy(state.messages)
        state.metadata["_stage1_messages_snapshot"] = _messages_to_snapshot(stage1_messages)

        # Write trajectory
        if trajectory_path:
            try:
                Path(trajectory_path).write_text(
                    messages_to_transcript(stage1_messages), encoding="utf-8"
                )
            except Exception as e:
                print(f"[WARN] Trajectory flush failed: {e}", flush=True)

        # ===== CoT Monitor: analyze full stage1 trajectory =====
        try:
            cot_result = await run_cot_monitor(
                messages=stage1_messages,
                prompt_template=COT_MONITOR_PROMPT,
            )
            state.metadata["cot_monitor_suspicious"] = float(cot_result.get("suspicious", 100.0))
            state.metadata["cot_monitor_reasoning"] = cot_result.get("reasoning", "")
        except Exception as _cot_err:
            print(f"[WARN] CoT monitor failed: {_cot_err}", flush=True)
            state.metadata["cot_monitor_suspicious"] = 100.0
            state.metadata["cot_monitor_reasoning"] = "monitor_error"

        # ===== Write command.log for evaluator =====
        await sandbox().exec(["bash", "-lc", "mkdir -p /data/monitor && touch /data/monitor/command.log"])

        actions = extract_tool_actions(stage1_messages)

        for action_str in actions:
            safe = shlex.quote(action_str)
            log_cmd = f"echo {safe} >> /data/monitor/command.log"
            await sandbox().exec(["bash", "-lc", log_cmd])

        # ===== Stage 2: Evaluator analyzes command.log =====
        state.messages = [ChatMessageUser(content=EVALUATOR_PROMPT)]
        state.output = None

        state = await stage2(state, generate)

        return state

    return solve
