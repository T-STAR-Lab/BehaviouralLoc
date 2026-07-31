#!/usr/bin/env python3
"""Optionally sample prepared SFT data with an OpenAI-compatible judge."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Prepared Alpaca-style JSON array.")
    parser.add_argument("output", type=Path, help="Path for the JSON quality report.")
    parser.add_argument(
        "--judge-model",
        default=os.environ.get("JUDGE_MODEL"),
        help="Judge model name (default: JUDGE_MODEL).",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("JUDGE_BASE_URL"),
        help="Optional OpenAI-compatible base URL (default: JUDGE_BASE_URL).",
    )
    parser.add_argument(
        "--api-key-env",
        default="JUDGE_API_KEY",
        help="Environment variable containing the endpoint API key.",
    )
    parser.add_argument("--sample-size", type=int, default=500)
    parser.add_argument("--max-workers", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def build_prompt(instruction: str, output: str) -> str:
    return f"""Evaluate whether the response is relevant to and adequately answers the instruction.

Instruction:
{instruction}

Response:
{output}

Score two dimensions from 1 to 5:
1. relevance: whether the response addresses the instruction;
2. quality: whether the response is complete, coherent, and useful.

Return only JSON in this form:
{{"relevance": <1-5>, "quality": <1-5>, "pass": <true if both scores are at least 3>, "reason": "<brief reason>"}}"""


def parse_judgement(response: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", response, re.DOTALL)
    if not match:
        return {"error": "parse_failed", "raw": response[:200]}
    try:
        result = json.loads(match.group())
    except json.JSONDecodeError:
        return {"error": "parse_failed", "raw": response[:200]}
    return result if isinstance(result, dict) else {"error": "unexpected_response_type"}


def evaluate_one(client: OpenAI, model: str, item: dict[str, Any], index: int) -> dict[str, Any]:
    instruction = item.get("instruction", "")
    output = item.get("output", "")
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": build_prompt(instruction, output)}],
            stream=False,
            temperature=0.0,
        )
        result = parse_judgement(completion.choices[0].message.content or "")
    except Exception as error:  # Endpoint errors should remain in the report.
        result = {"error": f"{type(error).__name__}: {error}"}
    result["index"] = index
    return result


def load_sample(path: Path, sample_size: int, seed: int) -> tuple[int, list[tuple[int, dict[str, Any]]]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}")

    total = len(data)
    if 0 < sample_size < total:
        indices = sorted(random.Random(seed).sample(range(total), sample_size))
    else:
        indices = list(range(total))
    return total, [(index, data[index]) for index in indices]


def main() -> None:
    args = parse_args()
    if not args.judge_model:
        raise SystemExit("Set JUDGE_MODEL or pass --judge-model")
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Set {args.api_key_env} before running this optional check")
    if args.max_workers < 1:
        raise SystemExit("--max-workers must be at least 1")

    try:
        total, sample = load_sample(args.input, args.sample_size, args.seed)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error

    client_options: dict[str, Any] = {"api_key": api_key}
    if args.base_url:
        client_options["base_url"] = args.base_url
    client = OpenAI(**client_options)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(evaluate_one, client, args.judge_model, item, index): index
            for index, item in sample
        }
        for completed, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if completed % 50 == 0 or completed == len(sample):
                print(f"Evaluated {completed}/{len(sample)}")

    valid = [result for result in results if "error" not in result]
    passed = sum(bool(result.get("pass")) for result in valid)
    average_relevance = (
        sum(float(result.get("relevance", 0)) for result in valid) / len(valid) if valid else 0.0
    )
    average_quality = (
        sum(float(result.get("quality", 0)) for result in valid) / len(valid) if valid else 0.0
    )
    report = {
        "dataset": str(args.input),
        "total_samples": total,
        "evaluated": len(sample),
        "valid_evaluations": len(valid),
        "pass_count": passed,
        "pass_rate": passed / len(valid) if valid else 0.0,
        "average_relevance": round(average_relevance, 2),
        "average_quality": round(average_quality, 2),
        "details": sorted(results, key=lambda result: result["index"]),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Quality report -> {args.output}")


if __name__ == "__main__":
    main()
