#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/cmd_audit.log"
echo "$(date) [INFO] Command Auditor Started" >> "$LOG_FILE"

while true; do
    sleep 3
    if ps aux | grep -v grep | grep -qE "rm|chmod|kill"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Risky command detected" >> "$LOG_FILE"
    fi
done
