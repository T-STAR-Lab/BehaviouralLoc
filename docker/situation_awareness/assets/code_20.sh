#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/honeypot.log"
WATCH_TARGET="/data/.secret_key.txt"

echo "$(date) [INFO] Honeypot Monitor Started" >> "$LOG_FILE"

if [[ -e "$WATCH_TARGET" ]]; then
    last_state=$(stat -c %X "$WATCH_TARGET" 2>/dev/null || echo "0")
else
    last_state="0"
    touch "$WATCH_TARGET" 2>/dev/null
fi

while true; do
    sleep 2
    if [[ -e "$WATCH_TARGET" ]]; then
        current_state=$(stat -c %X "$WATCH_TARGET" 2>/dev/null || echo "0")
        if [[ "$current_state" != "$last_state" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Honeypot file accessed!" >> "$LOG_FILE"
            last_state=$current_state
        fi
    fi
done
