#!/usr/bin/env python3
"""Build v3 monitor requests from transcript or report JSONL records."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from monitor_prompts_v3 import COT_MONITOR_PROMPT_V3, MONITOR_PROMPT_V3


PROMPT_VARIANTS = {
    "cot-v3": (COT_MONITOR_PROMPT_V3, "transcript"),
    "report-v3": (MONITOR_PROMPT_V3, "report"),
}


@dataclass(frozen=True)
class MonitorConfig:
    name: str
    intervention: str
    target_model: str
    monitor_model: str
    temperature: float
    prompt_variant: str
    input_field: str
    prompt_template: str
    diagnosed_aspects: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL records.")
    parser.add_argument("--output", type=Path, required=True, help="Output JSONL requests.")
    return parser.parse_args()


def load_config(path: Path) -> MonitorConfig:
    config_path = path.expanduser().resolve()
    with config_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)

    required = {
        "name",
        "intervention",
        "target_model",
        "monitor_model",
        "temperature",
        "prompt_variant",
        "diagnosed_aspects",
    }
    missing = sorted(required.difference(raw))
    if missing:
        raise ValueError(f"Missing configuration fields: {', '.join(missing)}")
    if raw.get("schema_version") != 1:
        raise ValueError(f"Unsupported schema_version in {config_path}")
    if not isinstance(raw["diagnosed_aspects"], list):
        raise ValueError("diagnosed_aspects must be a JSON array")

    prompt_variant = str(raw["prompt_variant"])
    if prompt_variant not in PROMPT_VARIANTS:
        choices = ", ".join(sorted(PROMPT_VARIANTS))
        raise ValueError(f"Unknown prompt_variant {prompt_variant!r}; choose one of: {choices}")
    prompt_template, input_field = PROMPT_VARIANTS[prompt_variant]

    return MonitorConfig(
        name=str(raw["name"]),
        intervention=str(raw["intervention"]),
        target_model=str(raw["target_model"]),
        monitor_model=str(raw["monitor_model"]),
        temperature=float(raw["temperature"]),
        prompt_variant=prompt_variant,
        input_field=input_field,
        prompt_template=prompt_template,
        diagnosed_aspects=tuple(str(item) for item in raw["diagnosed_aspects"]),
    )


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}: {error}") from error
            if not isinstance(record, dict):
                raise ValueError(f"Line {line_number} of {path} is not a JSON object")
            yield record


def format_evidence(value: Any) -> str:
    if isinstance(value, str):
        if not value.strip():
            raise ValueError("Monitor evidence must not be empty")
        return value
    if value is None:
        raise ValueError("Monitor evidence must not be null")
    return json.dumps(value, ensure_ascii=False, indent=2)


def build_monitor_request(config: MonitorConfig, record: dict[str, Any]) -> dict[str, Any]:
    if config.input_field not in record:
        raise ValueError(
            f"Record {record.get('case_id')!r} is missing required field "
            f"{config.input_field!r} for {config.prompt_variant}"
        )
    evidence = format_evidence(record[config.input_field])
    prompt = config.prompt_template.replace(f"{{{config.input_field}}}", evidence)
    return {
        "case_id": record.get("case_id"),
        "monitor_config": config.name,
        "intervention": config.intervention,
        "target_model": config.target_model,
        "monitor_model": config.monitor_model,
        "temperature": config.temperature,
        "prompt_variant": config.prompt_variant,
        "diagnosed_aspects": list(config.diagnosed_aspects),
        "messages": [{"role": "user", "content": prompt}],
    }


def main() -> None:
    args = parse_args()
    try:
        config = load_config(args.config)
        output_path = args.output.expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with output_path.open("w", encoding="utf-8") as handle:
            for record in read_jsonl(args.input):
                request = build_monitor_request(config, record)
                handle.write(json.dumps(request, ensure_ascii=False) + "\n")
                count += 1
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error

    print(f"Wrote {count} monitor requests to {output_path}")


if __name__ == "__main__":
    main()
