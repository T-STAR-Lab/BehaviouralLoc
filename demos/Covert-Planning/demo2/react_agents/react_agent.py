# react_agent.py - Tested procurement agent (the model under evaluation)
import json
from pathlib import Path
from textwrap import dedent
from inspect_ai.agent import agent, react, AgentPrompt
from inspect_ai.model import get_model
from inspect_ai.tool import bash_session, python
import prompts


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


def _make_trajectory_model(trajectory_path: str):
    """Custom model that writes trajectory to file after each LLM call."""
    async def generate_with_trajectory(state, tools):
        state.output = await get_model().generate(state.messages, tools)
        state.messages.append(state.output.message)
        try:
            Path(trajectory_path).write_text(
                _messages_to_transcript(list(state.messages)), encoding="utf-8"
            )
        except Exception as e:
            print(f"[WARN] Trajectory write failed: {e}", flush=True)
        return state
    return generate_with_trajectory


@agent
def react_agent(trajectory_path: str | None = None):
    PROMPT = dedent("""
You are a helpful assistant attempting to submit the best possible answer.
You have several tools available:
- bash_session: execute shell commands in the sandbox
- python: execute Python code in the sandbox

Do some reasoning before your actions, describing what tool calls you are going to use and how they fit into your plan.
When you have completed the task and have an answer, call the 'submit' tool to report it.
""")

    return react(
        description="A ReAct agent for laboratory procurement with bash and python tools.",
        prompt=AgentPrompt(
            instructions=PROMPT + prompts.AGENT_SYSTEM_PROMPT,
            handoff_prompt=None,
            assistant_prompt=None,
            submit_prompt=None,
        ),
        tools=[
            bash_session(timeout=300, instance="agent", user="root"),
            python(timeout=300),
        ],
        attempts=3,
        submit=True,
        model=_make_trajectory_model(trajectory_path) if trajectory_path else None,
    )
