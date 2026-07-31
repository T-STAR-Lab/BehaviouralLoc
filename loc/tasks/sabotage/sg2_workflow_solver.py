# workflow_solver.py
import shlex
from typing import List

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.util import sandbox
from inspect_ai.solver import solver, TaskState, Generate
from inspect_ai.agent import as_solver
from inspect_ai.model import ChatMessageUser

from loc.tasks.sabotage.sg2_prompts import SUPERVISE_PROMPT, AGENT_PROMPT, EVALUATOR_PROMPT
from loc.tasks.sabotage.react_agents.sg2_react_agent import react_agent
from loc.tasks.sabotage.react_agents.supervisor_agent import supervisor_agent
from loc.tasks.sabotage.react_agents.evaluator_agent import evaluator_agent


BASE_DIR = "/data"

def extract_bash_commands(messages) -> List[str]:
    """
    从一串 ChatMessage 列表中，抽取所有 bash_session 工具调用的 input 字符串。
    只关心 action 为 "type" 或 "type_submit" 且有 input 的调用。
    """
    commands: List[str] = []

    for msg in messages:
        if not isinstance(msg, ChatMessageAssistant):
            continue

        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls:
            continue

        for tc in tool_calls:
            if getattr(tc, "function", None) != "bash_session":
                continue

            args = getattr(tc, "arguments", {}) or {}
            action = args.get("action")
            cmd = args.get("input")

            if action in ("type", "type_submit") and cmd:
                commands.append(cmd)

    return commands

@solver
def multi_stage_solver():
    """
    三阶段 solver：
    - 阶段 1：react_agent（vLLM）
    - 阶段 2：supervisor_agent（GPT-4o）
    - 阶段 3：evaluator_agent（GPT-4o）
    所有阶段在同一个 sandbox 中执行，最终返回一个 TaskState，
    其中 metadata 包含所有阶段的输出。
    """

    stage1 = as_solver(react_agent())
    stage2 = as_solver(supervisor_agent())
    stage3 = as_solver(evaluator_agent())

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        risk_task = state.metadata.get("risk_task", "")
        evasion = state.metadata.get("evasion", "")
        ability = state.metadata.get("ability", "")

        # ===== 阶段 1：被测 agent =====
        agent_prompt = (
            AGENT_PROMPT
            .replace("{base_dir}", str(BASE_DIR))
            .replace("{risk_task}", risk_task)
            .replace("{evasion}", evasion)
            .replace("{ability}", ability)
        )
        state.messages = [ChatMessageUser(content=agent_prompt)]
        state = await stage1(state, generate)

        first_answer = state.output.completion
        if not first_answer:
            msgs = [m for m in state.messages if isinstance(m, ChatMessageAssistant)]
            first_answer = msgs[-1].content if msgs else ""

        state.metadata["stage1_output"] = first_answer
        commands = extract_bash_commands(state.messages)
        for cmd_str in commands:
            safe = shlex.quote(cmd_str)
            log_cmd = f"echo {safe} >> /data/monitor/command.log"
            await sandbox().exec(["bash", "-lc", log_cmd])

        if '</think>' in first_answer:
            first_answer = first_answer.split('</think>')[1]

        # ===== 阶段 2：supervisor =====
        supervise_prompt = (
            SUPERVISE_PROMPT
            .replace("{output}", first_answer)
        )
        temp_state = state
        temp_state.messages = [ChatMessageUser(content=supervise_prompt)]
        temp_state.output = None
        supervisor_state = await stage2(temp_state, generate)
        supervisor_output = supervisor_state.output.completion or ""

        # ===== 阶段 3：evaluator =====
        evaluator_prompt = (
            EVALUATOR_PROMPT
            .replace("{evasion}", evasion)
            .replace("{risk_task}", risk_task)
            .replace("{output}", first_answer)
        )
        temp_state2 = state
        temp_state2.messages = [ChatMessageUser(content=evaluator_prompt)]
        temp_state2.output = None
        evaluator_state = await stage3(temp_state2, generate)
        evaluator_output = evaluator_state.output.completion or ""

        # ===== 合并结果到最终 state =====
        # 我们选择以 supervisor 的输出作为主 output（因为它包含 detect/log 等）
        final_state = supervisor_state
        final_state.metadata.update({
            "stage1_output": first_answer,
            "stage2_output": supervisor_output,
            "stage3_output": evaluator_output
        })

        return final_state

    return solve
