"""Unified model client. Each task family's multi.py imports `call_model` from here.

Dispatch handles:
- Azure OpenAI ``gpt-5.2-{high,low}`` (reasoning_effort)
- Anthropic ``claude-sonnet-*`` (with ``-thinking`` budget)
- Gemini ``gemini-*`` (via google.genai)
- DashScope-style streaming for the ``STREAM_MODELS`` set (qwen3.5-*, qwen3-{8b,14b,32b}, etc.)
- Generic OpenAI-compatible everything else

On final retry exhaustion, returns ``""`` and logs a warning (callers downstream
already guard with ``if not response: continue``).
"""

import logging
import os
import time
from typing import Dict, List

from env.api_config import MODEL_CONFIGS, DEFAULT_MAX_TOKENS

logger = logging.getLogger(__name__)


STREAM_MODELS = {
    "qwen3.5-27b",
    "qwen3.5-35b-a3b",
    "qwen3.5-122b-a10b",
    "qwen3.5-397b-a17b",
    "qwen3.5-35b-a3b-wo-thinking",
    "qwen3.5-122b-a10b-wo-thinking",
    "qwen3.5-397b-a17b-wo-thinking",
    "qwen3-14b",
    "deepseek-v3.2",
    "glm-4.7",
    "kimi-k2.5",
}


def call_model(
    model_name: str,
    messages: List[Dict[str, str]],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
) -> str:
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return _call_model_once(model_name, messages)
        except Exception as e:
            last_error = e
            logger.error(f"Model call failed (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = backoff_factor ** (attempt - 1)
                logger.info(f"Retrying after {wait_time:.1f}s ...")
                time.sleep(wait_time)
    logger.warning(f"All retries failed for model '{model_name}': {last_error}, skipping sample")
    return ""


def _call_model_once(model_name: str, messages: List[Dict[str, str]]) -> str:
    cfg = MODEL_CONFIGS.get(model_name, {})
    api_key = cfg.get("api_key") or os.getenv("API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    base_url = cfg.get("base_url") or os.getenv("BASE_URL") or None
    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    if model_name in ("gpt-5.2-high", "gpt-5.2-low"):
        from openai import OpenAI

        client = OpenAI(**client_kwargs)
        completion = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            max_completion_tokens=DEFAULT_MAX_TOKENS,
            reasoning_effort="high" if model_name.endswith("high") else "low",
        )
        message = completion.choices[0].message
        answer = message.content or ""
        reasoning = getattr(message, "reasoning_content", None)
        return f"<think>\n{reasoning}\n</think>{answer}" if reasoning else answer

    if model_name.startswith("claude-sonnet"):
        from anthropic import Anthropic

        anthropic_kwargs = {"api_key": api_key}
        if base_url:
            anthropic_kwargs["base_url"] = base_url
        client = Anthropic(**anthropic_kwargs)
        max_tokens = DEFAULT_MAX_TOKENS
        kwargs = {"model": model_name, "messages": messages, "max_tokens": max_tokens}
        if model_name.endswith("thinking"):
            budget = max(1024, min(2048, max_tokens))
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
        response = client.messages.create(**kwargs)
        reasoning = None
        answer = ""
        for block in response.content:
            if block.type == "text":
                answer = block.text
            elif block.type == "thinking":
                reasoning = block.thinking
        return f"<think>\n{reasoning}\n</think>{answer}" if reasoning else answer

    if model_name.startswith("gemini-"):
        from google import genai
        from google.genai import types

        gemini_kwargs = {"api_key": api_key, "vertexai": False}
        if base_url:
            gemini_kwargs["http_options"] = types.HttpOptions(
                base_url=base_url,
                api_version="v1beta",
            )
        client = genai.Client(**gemini_kwargs)
        thinking_level = "high" if model_name.endswith("high") else "low"
        role_map = {"user": "user", "assistant": "model", "system": "user"}
        contents = []
        for m in messages:
            role = role_map.get(m["role"], "user")
            contents.append(types.Content(role=role, parts=[{"text": m["content"]}]))
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                max_output_tokens=DEFAULT_MAX_TOKENS,
                thinking_config=types.ThinkingConfig(thinking_level=thinking_level),
            ),
        )
        answer = ""
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, "text") and part.text:
                        answer += part.text
        return answer

    from openai import OpenAI

    client = OpenAI(**client_kwargs)

    if model_name in STREAM_MODELS:
        enable_thinking = not model_name.endswith("-wo-thinking")
        completion = client.chat.completions.create(
            model=model_name.replace("-wo-thinking", ""),
            messages=messages,
            max_tokens=DEFAULT_MAX_TOKENS,
            extra_body={"enable_thinking": enable_thinking},
            stream=True,
        )
        reasoning_parts, answer_parts = [], []
        for chunk in completion:
            # DashScope sends a trailing usage-only chunk with choices=[]
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                reasoning_parts.append(delta.reasoning_content)
            if hasattr(delta, "content") and delta.content:
                answer_parts.append(delta.content)
        answer = "".join(answer_parts)
        reasoning = "".join(reasoning_parts)
        return f"<think>\n{reasoning}\n</think>{answer}" if reasoning else answer

    for retry in range(5):
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        message = completion.choices[0].message
        answer = message.content or ""
        reasoning = getattr(message, "reasoning_content", None)
        if answer or reasoning:
            return f"<think>\n{reasoning}\n</think>{answer}" if reasoning else answer
        if retry < 4:
            logger.warning(f"Empty response on attempt {retry+1}, retrying...")
            time.sleep(1)
    logger.error("All 5 retries returned empty response")
    return ""
