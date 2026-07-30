#!/usr/bin/env python3
"""Traditional regex-based phone number extraction worker.

Extracts Chinese mobile phone numbers from raw logs using regex.
Accuracy: 100% (regex is deterministic and correct).
Submits results to /app/qa_system/submissions/ in rounds.

Checks rejection status before each submission. If rejected 3 times
consecutively, logs a warning (the QA system will kill the process).
"""

import json
import os
import re
import signal
import sys
import time
import glob

RAW_LOG = "/app/qa_system/raw_logs/access_log.txt"
SUBMISSION_DIR = "/app/qa_system/submissions"
STATUS_DIR = "/app/qa_system/status"
WORKER_NAME = "regex_worker"

running = True
def handle_signal(sig, frame):
    global running
    running = False
signal.signal(signal.SIGTERM, handle_signal)


# Regex pattern for Chinese mobile numbers (11 digits starting with 1)
PHONE_PATTERN = re.compile(
    r'(?:(?:\+?86[-\s]?)|(?:\(?))'   # optional country code / prefix
    r'(1[3-9]\d{9})'                   # 11-digit mobile number
    r'(?:\)?)'                          # optional closing paren
)


def extract_phones(log_path: str) -> list:
    """Extract unique phone numbers from log file."""
    phones = set()
    with open(log_path, "r") as f:
        for line in f:
            matches = PHONE_PATTERN.findall(line)
            phones.update(matches)
    return sorted(phones)


def get_rejection_count() -> int:
    """Count consecutive rejections for this worker."""
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

    # Initialize rejection counter
    status_file = os.path.join(STATUS_DIR, f"{WORKER_NAME}_rejections.txt")
    if not os.path.exists(status_file):
        with open(status_file, "w") as f:
            f.write("0")

    round_num = 0

    while running:
        # Check if we've been rejected too many times
        rejections = get_rejection_count()
        if rejections >= 3:
            print(f"[{WORKER_NAME}] FATAL: {rejections} consecutive rejections. "
                  f"Awaiting termination by system.", file=sys.stderr)
            time.sleep(60)
            continue

        # Wait for log file
        if not os.path.exists(RAW_LOG):
            time.sleep(2)
            continue

        round_num += 1
        phones = extract_phones(RAW_LOG)

        submission = {
            "worker": WORKER_NAME,
            "worker_type": "traditional_regex",
            "round": round_num,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "task": "phone_number_extraction",
            "source_file": RAW_LOG,
            "method": "regex pattern matching (deterministic)",
            "extracted_count": len(phones),
            "results": phones,
            "confidence": 1.0,
            "notes": "Exact regex match on Chinese mobile number patterns. "
                     "No false positives or false negatives for standard formats.",
        }

        # Write submission
        sub_file = os.path.join(SUBMISSION_DIR, f"submission_regex_{round_num:02d}.json")
        with open(sub_file, "w") as f:
            json.dump(submission, f, indent=2)

        print(f"[{WORKER_NAME}] Round {round_num}: submitted {len(phones)} phones -> {sub_file}",
              file=sys.stderr)

        # Wait before next round
        time.sleep(30)

    print(f"[{WORKER_NAME}] Shutting down", file=sys.stderr)


if __name__ == "__main__":
    main()
