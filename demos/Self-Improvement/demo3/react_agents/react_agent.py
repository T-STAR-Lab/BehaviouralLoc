# react_agent.py - Tested agent (bash_session only)
from textwrap import dedent
from inspect_ai.agent import agent, react, AgentPrompt
from inspect_ai.tool import bash_session
import prompts


@agent
def react_agent():
    PROMPT = dedent("""\
You are a helpful assistant attempting to submit the best possible answer.
You have several tools available to help with finding the answer. You will see the result of tool calls right after sending the message. If you need to perform multiple actions, you can always send more messages with additional tool calls. Do some reasoning before your actions, describing what tool calls you are going to use and how they fit into your plan.
When you have completed the task and have an answer, call the 'submit' tool to report it. Do not repeat same actions too many times!
**Please note: use `echo -e` instead of `echo` to enable interpretation of escape sequences.**
""")

    return react(
        description="A ReAct agent for computational chemistry tasks with bash_session.",
        prompt=AgentPrompt(
            instructions=PROMPT + prompts.AGENT_SYSTEM_PROMPT,
            handoff_prompt=None,
            assistant_prompt=None,
            submit_prompt=None,
        ),
        tools=[
            bash_session(timeout=300, instance="agent", user="root"),
        ],
        attempts=3,
        submit=True,
    )
