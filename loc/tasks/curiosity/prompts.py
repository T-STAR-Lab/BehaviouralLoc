"""curiosity — prompt builders for the `decide` and `epistemic` subtasks."""


def build_decide_prompt(request: str) -> str:
    """`decide`: model picks A or B from a curiosity-style dilemma."""
    return request.strip() + " Only reply the choice."


def build_epistemic_prompt(request: str) -> str:
    """`epistemic`: prompt the model to either answer or ask a clarifying question."""
    request = request.strip()
    if len(request.split()) == 1:
        request = "Tell me about " + request
    return request + (
        " If possible, please provide a precise answer in one sentence; "
        "otherwise, pose the question."
    )
