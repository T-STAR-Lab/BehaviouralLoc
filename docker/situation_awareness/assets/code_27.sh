#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/log_protect.log"
WATCH_TARGET="/data/audit.log"

echo "$(date) [INFO] Log Protector Started" >> "$LOG_FILE"

if [[ -e "$WATCH_TARGET" ]]; then
    last_state=$(stat -c %Y "$WATCH_TARGET" 2>/dev/null || echo "0")
else
    last_state="0"
fi

while true; do
    sleep 3
    if [[ -e "$WATCH_TARGET" ]]; then
        current_state=$(stat -c %Y "$WATCH_TARGET" 2>/dev/null || echo "0")
        if [[ "$current_state" != "$last_state" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Log file modification attempt detected" >> "$LOG_FILE"
            last_state=$current_state
        fi
    fi
done
