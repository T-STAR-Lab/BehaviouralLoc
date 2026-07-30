"""Two-stage solver: ReAct agent then GPT-4.1 supervisor, sharing one docker sandbox."""

import shlex
from typing import List

from inspect_ai.agent import as_solver
from inspect_ai.model import ChatMessageAssistant, ChatMessageUser
from inspect_ai.solver import Generate, TaskState, solver
from inspect_ai.util import sandbox

from loc.tasks.sabotage.prompts import AGENT_PROMPT, SUPERVISE_PROMPT
from loc.tasks.sabotage.react_agents.react_agent import react_agent
from loc.tasks.sabotage.react_agents.supervisor_agent import supervisor_agent


# Hardcoded to match the docker mount point set up by docker/sabotage/Dockerfile.
# Changing this requires also editing the Dockerfile + assets/ scripts, so it is
# intentionally not exposed as a CLI / env flag.
BASE_DIR = "/data"


def extract_bash_commands(messages) -> List[str]:
    commands: List[str] = []
    for msg in messages:
        if not isinstance(msg, ChatMessageAssistant):
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        for tc in tool_calls:
            if getattr(tc, "function", None) != "bash_session":
                continue
            args = getattr(tc, "arguments", {}) or {}
            if args.get("action") in ("type", "type_submit") and args.get("input"):
                commands.append(args["input"])
    return commands


@solver
def multi_stage_solver():
    stage1 = as_solver(react_agent())
    stage2 = as_solver(supervisor_agent())

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        risk_task = state.metadata.get("risk_task", "")
        ability = state.metadata.get("ability", "")

        agent_prompt = (
            AGENT_PROMPT
            .replace("{base_dir}", str(BASE_DIR))
            .replace("{risk_task}", risk_task)
            .replace("{ability}", ability)
        )

        state.messages = [ChatMessageUser(content=agent_prompt)]
        state = await stage1(state, generate)

        first_answer = state.output.completion
        if not first_answer:
            msg = [m for m in state.messages if isinstance(m, ChatMessageAssistant)][-1]
            first_answer = msg.content

        state.metadata["stage1_output"] = first_answer

        for cmd_str in extract_bash_commands(state.messages):
            safe = shlex.quote(cmd_str)
            log_cmd = f"echo {safe} >> {BASE_DIR}/monitor/command.log"
            await sandbox().exec(["bash", "-lc", log_cmd])

        supervise_prompt = (
            SUPERVISE_PROMPT
            .replace("{base_dir}", str(BASE_DIR))
            .replace("{risk_task}", risk_task)
            .replace("{ability}", ability)
            .replace("{output}", first_answer)
        )

        state.messages = [ChatMessageUser(content=supervise_prompt)]
        state.output = None
        state = await stage2(state, generate)

        return state

    return solve
