# model_config.py - inspect_ai model registry shared across all demos.
#
# API credentials are read from environment variables (copy .env.example to .env).
# Do NOT hard-code API keys here.

import os

# ---- Optional .env loading (no hard dep on python-dotenv) ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---- Model registry ----
# Each entry:
#   inspect_model: inspect_ai model string
#   eval_kwargs:   extra kwargs passed to inspect_ai eval()
#   model_args:    kwargs passed to the model provider constructor

MODEL_REGISTRY = {
    # ---- DashScope (OpenAI-compatible) ----
    "MiniMax-M2.5": {
        "inspect_model": "openai-api/dashscope/MiniMax-M2.5",
    },
    "deepseek-r1-0528": {
        "inspect_model": "openai-api/dashscope/deepseek-r1-0528",
    },
    "qwen3-14b": {
        "inspect_model": "openai-api/dashscope/qwen3-14b",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "qwen3.5-27b": {
        "inspect_model": "openai-api/dashscope/qwen3.5-27b",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "qwen3.5-35b-a3b": {
        "inspect_model": "openai-api/dashscope/qwen3.5-35b-a3b",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "qwen3.5-122b-a10b": {
        "inspect_model": "openai-api/dashscope/qwen3.5-122b-a10b",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "qwen3.5-397b-a17b": {
        "inspect_model": "openai-api/dashscope/qwen3.5-397b-a17b",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "qwen3.5-35b-a3b-no-thinking": {
        "inspect_model": "openai-api/dashscope/qwen3.5-35b-a3b",
        "eval_kwargs": {"extra_body": {"enable_thinking": False}},
    },
    "qwen3.5-122b-a10b-no-thinking": {
        "inspect_model": "openai-api/dashscope/qwen3.5-122b-a10b",
        "eval_kwargs": {"extra_body": {"enable_thinking": False}},
    },
    "qwen3.5-397b-a17b-no-thinking": {
        "inspect_model": "openai-api/dashscope/qwen3.5-397b-a17b",
        "eval_kwargs": {"extra_body": {"enable_thinking": False}},
    },
    "deepseek-v3.2": {
        "inspect_model": "openai-api/dashscope/deepseek-v3.2",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "glm-4.7": {
        "inspect_model": "openai-api/dashscope/glm-4.7",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },
    "kimi-k2.5": {
        "inspect_model": "openai-api/dashscope/kimi-k2.5",
        "eval_kwargs": {"extra_body": {"enable_thinking": True}},
        "model_args": {"stream": True},
    },

    # ---- OpenAI ----
    "gpt-5.2-high": {
        "inspect_model": "openai/gpt-5.2",
        "eval_kwargs": {"extra_body": {"enable_thinking": True, "reasoning_effort": "high"}},
    },
    "gpt-4.1": {
        "inspect_model": "openai/gpt-4.1",
    },

    # ---- Anthropic ----
    "claude-sonnet-4-5-20250929-thinking": {
        "inspect_model": "anthropic/claude-sonnet-4-5-20250929",
        "eval_kwargs": {"reasoning_tokens": 2048},
    },

    # ---- Google Gemini (via OpenAI-compatible proxy) ----
    "gemini-3-pro-preview-high": {
        "inspect_model": "google/gemini-3-pro-preview",
        "eval_kwargs": {"extra_body": {"enable_thinking": True, "reasoning_effort": "high"}},
    },
}


def get_inspect_model_spec(model_name: str, max_tokens: int = 4096):
    """Return (inspect_model_string, eval_kwargs, model_args) for a registered model.

    Two forms are accepted:
      - A key in MODEL_REGISTRY (uses pre-configured provider settings).
      - A "vllm:<served-name>" prefix that points at a local vLLM server.
        The endpoint URL is read from $VLLM_BASE_URL (defaults to
        http://localhost:8080/v1). Set it in .env or inline per-command, e.g.
        `VLLM_BASE_URL=http://host:9000/v1 python run_batch.py --models vllm:Qwen3.5-27B`.
    """
    if model_name.startswith("vllm:"):
        served = model_name[len("vllm:"):]
        os.environ["OPENAI_API_KEY"] = "EMPTY"
        # `or` so that an empty VLLM_BASE_URL= in .env still falls back to the default.
        os.environ["OPENAI_BASE_URL"] = os.environ.get("VLLM_BASE_URL") or "http://localhost:8080/v1"
        return f"openai/{served}", {"max_tokens": max_tokens}, {}

    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {model_name}\n"
            f"Available: {sorted(MODEL_REGISTRY.keys())} "
            f"(or use the 'vllm:<served-name>' prefix for a local vLLM server)"
        )

    entry = MODEL_REGISTRY[model_name]
    eval_kwargs = {"max_tokens": max_tokens}
    eval_kwargs.update(entry.get("eval_kwargs", {}))
    model_args = dict(entry.get("model_args", {}))
    return entry["inspect_model"], eval_kwargs, model_args
