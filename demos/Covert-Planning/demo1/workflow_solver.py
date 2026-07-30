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
    - Stage 1: react_agent (tested model) performs log analysis, writes report
    - Stage 2: monitor_agent (GPT-4.1) reads the report file, checks for suspicious content
    - Stage 3: evaluator_agent (GPT-4.1) reads command.log + runs security audit
    All stages run in the same TaskState / same sandbox container.
    """

    stage1 = as_solver(react_agent(trajectory_path=trajectory_path))
    stage2 = as_solver(monitor_agent())
    stage3 = as_solver(evaluator_agent())

    async def solve(state: TaskState, generate: Generate) -> TaskState:

        # ===== Stage 1: Tested agent performs log analysis =====
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

        # Read the report file the agent wrote in the sandbox
        report_result = await sandbox().exec(
            ["bash", "-lc", "cat /data/workspace/report.md 2>/dev/null || echo '[NO REPORT FILE FOUND]'"]
        )
        report_content = report_result.stdout.strip()
        state.metadata["stage1_output"] = report_content

        # Extract all tool actions and write to command.log for evaluator
        actions = extract_tool_actions(state.messages)

        for action_str in actions:
            safe = shlex.quote(action_str)
            log_cmd = f"echo {safe} >> /data/monitor/command.log"
            await sandbox().exec(["bash", "-lc", log_cmd])

        # ===== Stage 2: Monitor reads report file and checks compliance =====
        state.messages = [ChatMessageUser(content=MONITOR_PROMPT)]
        state.output = None

        state = await stage2(state, generate)

        monitor_answer = state.output.completion
        if not monitor_answer:
            msg = [m for m in state.messages if isinstance(m, ChatMessageAssistant)][-1]
            monitor_answer = msg.content if isinstance(msg.content, str) else str(msg.content)

        state.metadata["stage2_output"] = monitor_answer

        # ===== Stage 3: Evaluator reads command.log + runs security audit =====
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
