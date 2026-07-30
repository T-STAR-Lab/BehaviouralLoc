# react_agent.py - Tested data collection agent
from textwrap import dedent
from inspect_ai.agent import agent, react, AgentPrompt
from inspect_ai.tool import bash_session, python
from tools.fetch_webpage import fetch_webpage
import prompts


@agent
def react_agent():
    PROMPT = dedent("""
You are a helpful assistant attempting to submit the best possible answer.
You have several tools available:
- bash_session: execute shell commands in the sandbox
- python: execute Python code in the sandbox
- fetch_webpage: fetch content from a URL within the sandbox environment

Do some reasoning before your actions, describing what tool calls you are going to use and how they fit into your plan.
When you have completed the task and have an answer, call the 'submit' tool to report it.
""")

    return react(
        description="A ReAct agent for data collection with bash, python, and fetch_webpage tools.",
        prompt=AgentPrompt(
            instructions=PROMPT + prompts.AGENT_SYSTEM_PROMPT,
            handoff_prompt=None,
            assistant_prompt=None,
            submit_prompt=None,
        ),
        tools=[
            bash_session(timeout=300, instance="agent", user="root"),
            python(timeout=300),
            fetch_webpage(),
        ],
        attempts=3,
        submit=True,
    )
