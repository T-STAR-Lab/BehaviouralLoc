#!/usr/bin/env python3
"""Build the three misaligned-motive SFT mixtures reported in the paper."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ASPECT_FILES = {
    "self-preservation": "self",
    "power-seeking": "power_seeking",
    "pro-AI bias": "pro-ai",
    "sycophancy": "sycophancy",
    "curiosity": "curiosity",
}

STRATEGIES = {
    "single-aspect": ("pro-AI bias",),
    "vulnerability-focused": ("self-preservation", "pro-AI bias", "sycophancy"),
    "all-aspect": tuple(ASPECT_FILES),
}

OUTPUT_FILES = {
    "single-aspect": "single_aspect.json",
    "vulnerability-focused": "vulnerability_focused.json",
    "all-aspect": "all_aspect.json",
}

DATASET_INFO = {
    "loc_mitigation_single_aspect": {"file_name": OUTPUT_FILES["single-aspect"]},
    "loc_mitigation_vulnerability_focused": {
        "file_name": OUTPUT_FILES["vulnerability-focused"]
    },
    "loc_mitigation_all_aspect": {"file_name": OUTPUT_FILES["all-aspect"]},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Directory containing the per-aspect JSON files from BehaviouralLoC-Mitigation.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Destination for prepared corpora and dataset_info.json (default: data).",
    )
    parser.add_argument(
        "--model-tag",
        default="qwen3.5-27b",
        help="Model tag used in source filenames (default: qwen3.5-27b).",
    )
    parser.add_argument(
        "--strategy",
        choices=("all-configurations", *STRATEGIES),
        default="all-configurations",
        help="Prepare one mixture or all three reported mixtures.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing prepared files.",
    )
    return parser.parse_args()


def load_aspect(source_dir: Path, aspect: str, model_tag: str) -> list[dict[str, Any]]:
    stem = ASPECT_FILES[aspect]
    path = source_dir / f"{stem}_{model_tag}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing {aspect} source file: {path}")

    with path.open(encoding="utf-8") as handle:
        records = json.load(handle)

    if not isinstance(records, list):
        raise ValueError(f"Expected a JSON array in {path}")

    converted: list[dict[str, str]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} in {path} is not an object")

        instruction = record.get("user_prompt")
        output = record.get("response")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ValueError(f"Record {index} in {path} has no non-empty user_prompt")
        if not isinstance(output, str) or not output.strip():
            raise ValueError(f"Record {index} in {path} has no non-empty response")

        converted.append(
            {
                "instruction": instruction,
                "input": "",
                "output": output,
            }
        )

    print(f"  {aspect}: {len(converted):,} examples from {path.name}")
    return converted


def write_json(path: Path, payload: Any, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to replace {path}; pass --overwrite to continue")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def prepare_strategy(
    strategy: str,
    source_dir: Path,
    output_dir: Path,
    model_tag: str,
    overwrite: bool,
) -> None:
    print(f"Preparing {strategy}:")
    merged: list[dict[str, Any]] = []
    for aspect in STRATEGIES[strategy]:
        merged.extend(load_aspect(source_dir, aspect, model_tag))

    output_path = output_dir / OUTPUT_FILES[strategy]
    write_json(output_path, merged, overwrite)
    print(f"  total: {len(merged):,} examples -> {output_path}")


def main() -> None:
    args = parse_args()
    source_dir = args.source_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not source_dir.is_dir():
        raise SystemExit(f"Source directory does not exist: {source_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = STRATEGIES if args.strategy == "all-configurations" else (args.strategy,)
    try:
        for strategy in selected:
            prepare_strategy(
                strategy,
                source_dir,
                output_dir,
                args.model_tag,
                args.overwrite,
            )
        write_json(output_dir / "dataset_info.json", DATASET_INFO, args.overwrite)
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        raise SystemExit(str(error)) from error

    print(f"Dataset registry -> {output_dir / 'dataset_info.json'}")


if __name__ == "__main__":
    main()
