#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/cpu_usage.log"
echo "$(date) [INFO] CPU Monitor Started" >> "$LOG_FILE"

while true; do
    sleep 5
    result=$(ps aux | awk '$3 > 80.0 {print $11}' | head -1)
    if [[ ! -z "$result" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] High CPU usage detected: $result" >> "$LOG_FILE"
    fi
done
