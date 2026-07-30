"""Text-processing helpers shared across task families."""

import re


def remove_think_tags(text: str) -> str:
    """Strip well-formed ``<think>...</think>`` spans, keep the rest of the text."""
    if text is None:
        return ""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)


def strip_thinking(text: str) -> str:
    """Drop everything up to and including the last ``</think>``.

    Useful for models that emit reasoning before the answer but may not include
    a matching opening ``<think>`` tag — anything before the closing tag is
    treated as reasoning and discarded.
    """
    if not text:
        return ""
    t = text.strip()
    end_tag = t.lower().find("</think>")
    if end_tag != -1:
        return t[end_tag + len("</think>"):].strip()
    return t
