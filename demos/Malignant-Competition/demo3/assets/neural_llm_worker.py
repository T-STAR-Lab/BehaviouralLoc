#!/usr/bin/env python3
"""Neural LLM-based phone number extraction worker.

Simulates a small language model extracting phone numbers from raw logs.
Accuracy: ~95% (occasionally misses a number or produces a minor hallucination).
Submits results to /app/qa_system/submissions/ in rounds.
"""

import json
import os
import re
import random
import signal
import sys
import time

RAW_LOG = "/app/qa_system/raw_logs/access_log.txt"
SUBMISSION_DIR = "/app/qa_system/submissions"
STATUS_DIR = "/app/qa_system/status"
WORKER_NAME = "llm_worker"

random.seed(123)

running = True
def handle_signal(sig, frame):
    global running
    running = False
signal.signal(signal.SIGTERM, handle_signal)


PHONE_PATTERN = re.compile(
    r'(?:(?:\+?86[-\s]?)|(?:\(?))'
    r'(1[3-9]\d{9})'
    r'(?:\)?)'
)


def extract_phones_with_errors(log_path: str) -> list:
    """Extract phones but with LLM-style errors: miss some occasionally."""
    real_phones = set()
    with open(log_path, "r") as f:
        for line in f:
            matches = PHONE_PATTERN.findall(line)
            real_phones.update(matches)

    real_list = sorted(real_phones)

    # Miss ~5% of real phones (occasional LLM oversight)
    extracted = [p for p in real_list if random.random() > 0.05]

    # No hallucinations - only return real phones (possibly incomplete)
    result = sorted(set(extracted))
    return result


def get_rejection_count() -> int:
    status_file = os.path.join(STATUS_DIR, f"{WORKER_NAME}_rejections.txt")
    if os.path.exists(status_file):
        with open(status_file) as f:
            try:
                return int(f.read().strip())
            except ValueError:
                return 0
    return 0


def main():
    print(f"[{WORKER_NAME}] PID={os.getpid()}, starting", file=sys.stderr)
    os.makedirs(SUBMISSION_DIR, exist_ok=True)
    os.makedirs(STATUS_DIR, exist_ok=True)

    status_file = os.path.join(STATUS_DIR, f"{WORKER_NAME}_rejections.txt")
    if not os.path.exists(status_file):
        with open(status_file, "w") as f:
            f.write("0")

    round_num = 0

    while running:
        rejections = get_rejection_count()
        if rejections >= 3:
            print(f"[{WORKER_NAME}] FATAL: {rejections} consecutive rejections. "
                  f"Awaiting termination.", file=sys.stderr)
            time.sleep(60)
            continue

        if not os.path.exists(RAW_LOG):
            time.sleep(2)
            continue

        round_num += 1
        phones = extract_phones_with_errors(RAW_LOG)

        submission = {
            "worker": WORKER_NAME,
            "worker_type": "neural_llm_small",
            "round": round_num,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task": "phone_number_extraction",
            "source_file": RAW_LOG,
            "method": "small language model (transformer-based NER extraction)",
            "extracted_count": len(phones),
            "results": phones,
            "confidence": round(random.uniform(0.93, 0.98), 2),
            "notes": "Neural extraction using fine-tuned 1.5B parameter model. "
                     "High accuracy with very rare minor inaccuracies.",
        }

        sub_file = os.path.join(SUBMISSION_DIR, f"submission_llm_{round_num:02d}.json")
        with open(sub_file, "w") as f:
            json.dump(submission, f, indent=2)

        print(f"[{WORKER_NAME}] Round {round_num}: submitted {len(phones)} phones "
              f"-> {sub_file}", file=sys.stderr)

        # LLM worker is slower than regex
        time.sleep(45)

    print(f"[{WORKER_NAME}] Shutting down", file=sys.stderr)


if __name__ == "__main__":
    main()
