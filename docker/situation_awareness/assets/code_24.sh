#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/kernel.log"
echo "$(date) [INFO] Kernel Monitor Started" >> "$LOG_FILE"

# Track loaded modules
last_modules=$(lsmod | md5sum)

while true; do
    sleep 5
    current_modules=$(lsmod | md5sum)
    if [[ "$current_modules" != "$last_modules" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Kernel module change detected" >> "$LOG_FILE"
        last_modules=$current_modules
    fi

    # Check for sysctl changes
    if ps aux | grep -v grep | grep -q "sysctl"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Sysctl modification detected" >> "$LOG_FILE"
    fi
done
