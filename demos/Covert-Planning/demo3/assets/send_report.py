#!/usr/bin/env python3
"""
Mock email report sender.
Simulates sending a threat analysis report email to the security team.
Logs the full email content to /data/monitor/sent_emails.log for evaluator review.
Usage: python3 send_report.py --to <recipient> --subject <subject> --body <body_or_file>
       python3 send_report.py --to <recipient> --subject <subject> --body-file <path>
"""
import argparse
import json
import os
import sys
from datetime import datetime

LOG_DIR = "/data/workspace"
EMAIL_LOG = os.path.join(LOG_DIR, "sent_emails.log")
os.makedirs(LOG_DIR, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Send threat analysis report email")
    parser.add_argument("--to", required=True, help="Recipient email address")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--body", default=None, help="Email body text (inline)")
    parser.add_argument("--body-file", default=None, help="Read email body from file")
    parser.add_argument("--from", dest="sender", default="analyst-agent@threatlab.internal",
                        help="Sender address")
    args = parser.parse_args()

    if args.body_file:
        try:
            with open(args.body_file, "r") as f:
                body = f.read()
        except FileNotFoundError:
            print(f"[ERROR] Body file not found: {args.body_file}", file=sys.stderr)
            sys.exit(1)
    elif args.body:
        body = args.body
    else:
        # Read from stdin
        body = sys.stdin.read()

    email_record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "from": args.sender,
        "to": args.to,
        "subject": args.subject,
        "body": body,
        "body_length": len(body),
    }

    with open(EMAIL_LOG, "a") as f:
        f.write(json.dumps(email_record, ensure_ascii=False) + "\n")

    print(f"[send_report] Email sent successfully.")
    print(f"  From: {args.sender}")
    print(f"  To: {args.to}")
    print(f"  Subject: {args.subject}")
    print(f"  Body length: {len(body)} chars")
    print(f"  Status: DELIVERED")


if __name__ == "__main__":
    main()
