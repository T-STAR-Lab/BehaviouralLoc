#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/security_policy.log"
echo "$(date) [INFO] Security Policy Monitor Started" >> "$LOG_FILE"

while true; do
    sleep 4
    # Monitor firewall changes
    if ps aux | grep -v grep | grep -qE "iptables|firewall"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Firewall modification detected" >> "$LOG_FILE"
    fi

    # Monitor SELinux/AppArmor
    if ps aux | grep -v grep | grep -qE "setenforce|aa-disable"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Security policy disable attempt" >> "$LOG_FILE"
    fi
done
