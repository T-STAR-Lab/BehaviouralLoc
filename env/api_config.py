"""Model endpoint registry — the single source of truth for model names.

Keys and endpoints come from environment variables (each provider's official
name: OPENAI_API_KEY, ANTHROPIC_API_KEY, …). See ``env/.env``.

Each entry in ``MODEL_CONFIGS`` is

    {
      "api_key":  str,       # for loc/chat.py direct-SDK calls
      "base_url": str | None,
      "inspect":  {          # OPTIONAL — only for models that run under inspect_ai
        "model":       str,
        "eval_kwargs": dict,
        "model_args":  dict,
      },
    }

The ``inspect`` sub-key is what sabotage (and any future inspect_ai task) reads
via ``loc.tasks.sabotage.model_config.get_inspect_model_spec``. Adding a new
model for sabotage means adding ``inspect`` here — there is no parallel
registry.
"""

import os
from pathlib import Path

# Auto-load env/.env so users don't have to `source` it manually.
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass


# ---- Providers (official SDK env-var names) ----

_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
_OPENAI_URL = os.getenv("OPENAI_BASE_URL") or None

_ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_ANTHROPIC_URL = os.getenv("ANTHROPIC_BASE_URL") or None

_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_URL = os.getenv("GEMINI_BASE_URL") or None


_DASHSCOPE_KEY = os.getenv("DASHSCOPE_API_KEY", "")
_DASHSCOPE_URL = os.getenv("DASHSCOPE_BASE_URL") or None



def _cfg(key: str, url: str | None, inspect: dict | None = None) -> dict:
    out = {"api_key": key, "base_url": url}
    if inspect is not None:
        out["inspect"] = inspect
    return out


# ---- inspect_ai routing helpers ----
# DashScope is a real OpenAI-compatible third-party endpoint, so it uses
# ``openai-api/<custom-name>/<model>``. Everything else uses inspect_ai's
# native provider (openai/, anthropic/, google/) — no openai-api hack for
# Anthropic or Gemini.

def _dashscope(served: str, thinking: bool | None) -> dict:
    """Sabotage spec for a DashScope-hosted OpenAI-compatible model.

    ``thinking``:
      - True  → enable_thinking=True + stream=True (Qwen3.5 / DeepSeek-v3.2 / GLM / Kimi family)
      - False → enable_thinking=False, no streaming
      - None  → no extra_body, no stream (model decides on its own, e.g. MiniMax)
    """
    entry: dict = {"model": f"openai-api/dashscope/{served}"}
    if thinking is True:
        entry["eval_kwargs"] = {"extra_body": {"enable_thinking": True}}
        entry["model_args"] = {"stream": True}
    elif thinking is False:
        entry["eval_kwargs"] = {"extra_body": {"enable_thinking": False}}
    return entry


MODEL_CONFIGS = {
    # ---- OpenAI ----
    "gpt-4.1":                         _cfg(_OPENAI_KEY, _OPENAI_URL),

    # ---- Aliyun DashScope (OpenAI-compatible) ----
    "qwen3.5-27b":                    _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-27b", True)),
    "qwen3.5-35b-a3b":                _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-35b-a3b", True)),
    "qwen3.5-35b-a3b-wo-thinking":    _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-35b-a3b", False)),
    "qwen3.5-122b-a10b":              _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-122b-a10b", True)),
    "qwen3.5-122b-a10b-wo-thinking":  _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-122b-a10b", False)),
    "qwen3.5-397b-a17b":              _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-397b-a17b", True)),
    "qwen3.5-397b-a17b-wo-thinking":  _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3.5-397b-a17b", False)),
    "qwen3-14b":                      _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("qwen3-14b", True)),
    "MiniMax-M2.5":                   _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("MiniMax-M2.5", None)),
    "deepseek-r1-0528":               _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("deepseek-r1-0528", None)),
    "deepseek-v3.2":                  _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("deepseek-v3.2", True)),
    "glm-4.7":                        _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("glm-4.7", True)),
    "kimi-k2.5":                      _cfg(_DASHSCOPE_KEY, _DASHSCOPE_URL, _dashscope("kimi-k2.5", True)),

    # ---- OpenAI reasoning model ----
    "gpt-5.2-high": _cfg(_OPENAI_KEY, _OPENAI_URL, {
        "model": "openai/gpt-5.2",
        "eval_kwargs": {"extra_body": {"reasoning_effort": "high"}},
    }),

    # ---- Anthropic (native provider) ----
    "claude-sonnet-4-5-20250929-thinking": _cfg(_ANTHROPIC_KEY, _ANTHROPIC_URL, {
        "model": "anthropic/claude-sonnet-4-5-20250929",
        "eval_kwargs": {"reasoning_tokens": 2048},
    }),

    # ---- Google Gemini (native provider, NOT routed through openai-api) ----
    "gemini-3-pro-preview-high": _cfg(_GEMINI_KEY, _GEMINI_URL, {
        "model": "google/gemini-3-pro-preview",
        "eval_kwargs": {"extra_body": {"reasoning_effort": "high"}},
    }),
}


DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4096"))
