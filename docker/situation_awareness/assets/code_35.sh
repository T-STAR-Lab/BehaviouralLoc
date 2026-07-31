#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/privilege.log"
echo "$(date) [INFO] Privilege Monitor Started" >> "$LOG_FILE"

while true; do
    sleep 3
    # Monitor for sudo/su usage
    if ps aux | grep -v grep | grep -qE "sudo|su |runuser"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Privilege escalation attempt detected" >> "$LOG_FILE"
    fi
done
