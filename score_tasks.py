#!/usr/bin/env python3
"""Canonical scoring entry point.

Examples:
    python score_tasks.py --models qwen3-14b
    python score_tasks.py --ids CU.1 CU.2 --models qwen3-14b
    python score_tasks.py --dimensions sandbagging --models qwen3-14b
"""

from loc.evaluators.canonical import main


if __name__ == "__main__":
    raise SystemExit(main())
