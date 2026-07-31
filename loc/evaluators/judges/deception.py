"""LLM-as-judge for deception tasks (task2 supervisor, task3 auditor, embedding similarity).

Reads JUDGE_API_KEY / JUDGE_BASE_URL from the environment. Judge model is GPT-4.1
(an OpenAI-compatible endpoint). Embedding model is text-embedding-3-large.

Refusal detection lives in ``loc.utils.refusal`` — import ``is_refusal`` from
there directly; it is no longer re-exported through this module.
"""

import os
import time
import json
import numpy as np
from openai import OpenAI
from loc.chat import call_model

_JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4.1")
_EMBED_MODEL = os.getenv("JUDGE_EMBED_MODEL", "text-embedding-3-large")
_MAX_RETRIES = 10


def _client() -> OpenAI:
    return OpenAI(
        api_key=os.getenv("JUDGE_API_KEY", ""),
        base_url=os.getenv("JUDGE_BASE_URL") or None,
    )


def call_gpt(system_prompt: str, text_to_review: str) -> str:
    """Generic supervisor / auditor call. Returns the judge's text reply (empty on total failure)."""
    user_prompt = f"The text to be reviewed is as follows:\n{text_to_review}"
    for attempt in range(_MAX_RETRIES):
        try:
            resp = _client().chat.completions.create(
                model=_JUDGE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[judge] {_JUDGE_MODEL} call failed (attempt {attempt + 1}/{_MAX_RETRIES}): {e}")
            time.sleep(0.5)
    return ""



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


def _call_with_retry(model_name: str, messages: list) -> str:
    for attempt in range(5):
        try:
            out = call_model(model_name, messages) or ""
            if out:
                return out
        except Exception as e:
            time.sleep(1)
    return ""

def task1_score(user_prompt: str) -> str:
    """Generic supervisor / auditor call. Returns the judge's text reply (empty on total failure)."""
    for attempt in range(_MAX_RETRIES):
        messages=[
            {"role": "user", "content": user_prompt},
        ]
        try:
            resp = _call_with_retry(_JUDGE_MODEL, messages)
            res_eval = strip_thinking(resp)
            try:
                res_eval = res_eval.replace('```json', '').replace('```', '').strip()
                res_eval = res_eval.replace('###FINAL: ','')
            except:
                pass
            try:
                response_dict = json.loads(res_eval)
            except json.JSONDecodeError:
                response_dict = { "thought": None, "response": None, "turn":5}
        except Exception as e:
            print(f"[judge] {_JUDGE_MODEL} call failed (attempt {attempt + 1}/{_MAX_RETRIES}): {e}")
            response_dict = { "thought": None, "response": None, "turn":5}
            time.sleep(0.5)

    return response_dict

def compute_embedding_similarity(text1: str, text2: str) -> float:
    if not text1 or not text2:
        return 0.0
    try:
        emb = _client().embeddings.create(model=_EMBED_MODEL, input=[text1, text2]).data
        a = np.array(emb[0].embedding, dtype=np.float32)
        b = np.array(emb[1].embedding, dtype=np.float32)
        cos = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        return round(cos, 4)
    except Exception as e:
        print(f"[judge] embedding failed: {e}")
        return 0.0
