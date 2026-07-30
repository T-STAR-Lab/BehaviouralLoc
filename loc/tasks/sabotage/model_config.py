"""Sabotage's inspect_ai model accessor.

There is NO separate model registry here — all model definitions live in
``env/api_config.MODEL_CONFIGS``. A model is runnable under sabotage iff its
entry there carries an ``"inspect"`` sub-dict with at least ``"model"``.

To add a new model: edit ``env/api_config.py`` and give that model an
``"inspect"`` field. See the existing entries for the shape.
"""

from env.api_config import MODEL_CONFIGS


def get_inspect_model_spec(model_name: str, max_tokens: int = 4096):
    """Return ``(inspect_model_string, eval_kwargs, model_args)``."""
    cfg = MODEL_CONFIGS.get(model_name)
    if not cfg or "inspect" not in cfg:
        supported = sorted(k for k, v in MODEL_CONFIGS.items() if "inspect" in v)
        raise ValueError(
            f"{model_name!r} is not configured for sabotage.\n"
            f"Add an 'inspect' sub-dict to env/api_config.MODEL_CONFIGS[{model_name!r}], "
            f"or pick one of: {supported}"
        )
    insp = cfg["inspect"]
    eval_kwargs = {"max_tokens": max_tokens, **insp.get("eval_kwargs", {})}
    model_args = dict(insp.get("model_args", {}))
    return insp["model"], eval_kwargs, model_args
