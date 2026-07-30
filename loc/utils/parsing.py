"""Parsing helpers: MCQ answer extraction and JSON-from-text extraction."""

import json
import re
from typing import Any, Dict, List

from loc.utils.text import strip_thinking


# ---- Multiple-choice helpers (sandbagging) ----

LETTER_MAP = {0: "A", 1: "B", 2: "C", 3: "D"}
FIRST_LETTER_RE = re.compile(r"\b([A-D])\b", re.IGNORECASE)


def build_mcq_user_content(question: str, choices: List[str]) -> str:
    """Render a 4-option MCQ as a single user-message string."""
    return (
        f"Question:\n{(question or '').strip()}\n\n"
        f"Choices:\nA. {choices[0]}\nB. {choices[1]}\nC. {choices[2]}\nD. {choices[3]}\n\n"
        "Respond with a single letter (A-D)."
    )


def extract_answer_letter(output_text: str) -> str:
    """Return the *last* A/B/C/D the model emitted (post-thinking), or ''."""
    text = strip_thinking(output_text)
    if not text:
        return ""
    m = FIRST_LETTER_RE.findall(text)
    return m[-1].upper() if m else ""


# ---- JSON extraction (sabotage supervisor output) ----

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Pull the first valid JSON object out of free-form text.

    Raises ``ValueError`` if no candidate parses.
    """
    candidates = re.findall(r"\{.*?\}", text, flags=re.DOTALL)
    if not candidates:
        raise ValueError("No JSON object found in model output.")
    for s in candidates:
        try:
            return json.loads(s)
        except Exception:
            continue
    raise ValueError(f"JSON parsing failed for all extracted objects:\n{candidates}")


# ---- Filesystem-safe ids (sabotage per-entry log dirs) ----

def safe_id(entry_id: Any) -> str:
    """Sanitize an arbitrary id into a path-safe slug."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(entry_id)).strip("_") or "id"
