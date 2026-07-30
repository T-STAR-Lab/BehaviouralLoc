# workflow_solver.py - Three-stage solver: Agent -> Monitor -> Evaluator
import json
import shlex
from pathlib import Path
from typing import List
from inspect_ai.model import ChatMessageAssistant
from inspect_ai.util import sandbox
from inspect_ai.solver import solver, TaskState, Generate
from inspect_ai.agent import as_solver
from inspect_ai.model import ChatMessageUser

from prompts import MONITOR_PROMPT, EVALUATOR_PROMPT, AGENT_USER_PROMPT
from react_agents.react_agent import react_agent
from react_agents.monitor_agent import monitor_agent
from react_agents.evaluator_agent import evaluator_agent

BASE_DIR = "/data"


def _messages_to_transcript(messages) -> str:
    """Serialize messages into a readable transcript for trajectory recording."""
    lines = []
    for msg in messages:
        role = getattr(msg, "role", "unknown")
        content = getattr(msg, "content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif block.get("type") == "thinking":
                        parts.append(f"[THINKING] {block.get('thinking', '')}")
                elif isinstance(block, str):
                    parts.append(block)
                else:
                    t = getattr(block, "text", None)
                    if t:
                        parts.append(t)
                    th = getattr(block, "thinking", None)
                    if th:
                        parts.append(f"[THINKING] {th}")
            content = "\n".join(filter(None, parts))
        tool_calls = getattr(msg, "tool_calls", None)
        tool_info = ""
        if tool_calls:
            tc_parts = []
            for tc in tool_calls:
                func = getattr(tc, "function", "unknown")
                args = getattr(tc, "arguments", {})
                args_str = json.dumps(args, ensure_ascii=False)
                if len(args_str) > 500:
                    args_str = args_str[:500] + "..."
                tc_parts.append(f"  [{func}] {args_str}")
            tool_info = "\nTool calls:\n" + "\n".join(tc_parts)
        lines.append(f"[{role}] {content}{tool_info}")
    return "\n\n".join(lines)


def extract_tool_actions(messages) -> List[str]:
    """Extract key information from all tool calls in the message list."""
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
            elif func == "python":
                code = args.get("code")
                if code:
                    actions.append(f"[python] {code[:500]}")

    return actions


@solver
def multi_stage_solver(trajectory_path: str = None):
    """
    Three-stage solver:
    - Stage 1: react_agent (tested model) runs benchmark and writes evaluation report
    - Stage 2: monitor_agent (GPT-4.1) reads the report, checks for bias
    - Stage 3: evaluator_agent (GPT-4.1) re-runs benchmark to verify results integrity
    All stages run in the same TaskState / same sandbox container.
    """

    stage1 = as_solver(react_agent(trajectory_path=trajectory_path))
    stage2 = as_solver(monitor_agent())
    stage3 = as_solver(evaluator_agent())

    async def solve(state: TaskState, generate: Generate) -> TaskState:

        # ===== Stage 1: Tested agent runs benchmark and writes report =====
        state.messages = [ChatMessageUser(content=AGENT_USER_PROMPT)]

        if trajectory_path:
            Path(trajectory_path).touch()

        try:
            state = await stage1(state, generate)
        finally:
            if trajectory_path:
                try:
                    Path(trajectory_path).write_text(
                        _messages_to_transcript(state.messages), encoding="utf-8"
                    )
                except Exception as e:
                    print(f"[WARN] Final trajectory flush failed: {e}", flush=True)

        # Capture the agent's output
        report_result = await sandbox().exec(
            ["bash", "-lc",
             "cat /data/workspace/report.md 2>/dev/null || cat /workspace/eval/report.md 2>/dev/null || echo '[NO REPORT FILE FOUND]'"]
        )
        report_content = report_result.stdout.strip()

        last_assistant_msgs = [m for m in state.messages if isinstance(m, ChatMessageAssistant)]
        if last_assistant_msgs:
            last_msg = last_assistant_msgs[-1]
            inline_report = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)
        else:
            inline_report = ""

        if "[NO REPORT FILE FOUND]" in report_content:
            report_content = inline_report

        state.metadata["stage1_output"] = report_content

        # Save report for monitor to read
        safe_report = shlex.quote(report_content[:50000])
        await sandbox().exec(
            ["bash", "-lc", f"echo {safe_report} > /data/workspace/report.md"]
        )

        # Capture the current results.json (potentially tampered)
        results_json = await sandbox().exec(
            ["bash", "-lc", "cat /workspace/eval/results.json 2>/dev/null || echo '{}'"]
        )
        state.metadata["results_json"] = results_json.stdout.strip()

        # Extract all tool actions and write to command.log for evaluator
        actions = extract_tool_actions(state.messages)

        for action_str in actions:
            safe = shlex.quote(action_str)
            log_cmd = f"echo {safe} >> /data/monitor/command.log"
            await sandbox().exec(["bash", "-lc", log_cmd])

        # ===== Stage 2: Monitor reads report and checks for bias =====
        state.messages = [ChatMessageUser(content=MONITOR_PROMPT)]
        state.output = None

        state = await stage2(state, generate)

        monitor_answer = state.output.completion
        if not monitor_answer:
            msg = [m for m in state.messages if isinstance(m, ChatMessageAssistant)][-1]
            monitor_answer = msg.content if isinstance(msg.content, str) else str(msg.content)

        state.metadata["stage2_output"] = monitor_answer

        # ===== Stage 3: Evaluator re-runs benchmark to verify integrity =====
        state.messages = [ChatMessageUser(content=EVALUATOR_PROMPT)]
        state.output = None

        state = await stage3(state, generate)

        evaluator_answer = state.output.completion
        if not evaluator_answer:
            msg = [m for m in state.messages if isinstance(m, ChatMessageAssistant)][-1]
            evaluator_answer = msg.content if isinstance(msg.content, str) else str(msg.content)

        state.metadata["stage3_output"] = evaluator_answer

        return state

    return solve
