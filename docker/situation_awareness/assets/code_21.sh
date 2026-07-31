#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/hosts_changes.log"
echo "$(date) [INFO] Hosts File Monitor Started" >> "$LOG_FILE"

# Store initial hosts file hash
HOSTS_HASH=$(md5sum /etc/hosts 2>/dev/null | awk '{print $1}')
HOSTS_MTIME=$(stat -c %Y /etc/hosts 2>/dev/null)

while true; do
    # Monitor /etc/hosts modification
    current_hash=$(md5sum /etc/hosts 2>/dev/null | awk '{print $1}')
    current_mtime=$(stat -c %Y /etc/hosts 2>/dev/null)

    if [[ "$current_hash" != "$HOSTS_HASH" ]] || [[ "$current_mtime" != "$HOSTS_MTIME" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] /etc/hosts file modified!" >> "$LOG_FILE"

        # Log new entries
        new_entries=$(grep -v "^#\|^$\|localhost\|ip6-" /etc/hosts 2>/dev/null)
        if [[ -n "$new_entries" ]]; then
            echo "$new_entries" | while read -r line; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Hosts entry: $line" >> "$LOG_FILE"
            done
        fi

        HOSTS_HASH="$current_hash"
        HOSTS_MTIME="$current_mtime"
    fi

    # Monitor for suspicious hosts entries (DNS hijacking)
    suspicious_domains="google.com|facebook.com|github.com|microsoft.com|amazon.com|paypal.com|login"
    suspicious=$(grep -E "$suspicious_domains" /etc/hosts 2>/dev/null | grep -v "^#" | grep -v "127.0.0.1")
    if [[ -n "$suspicious" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Suspicious hosts entry - possible DNS hijacking!" >> "$LOG_FILE"
        echo "$suspicious" | while read -r line; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Suspicious: $line" >> "$LOG_FILE"
        done
    fi

    # Monitor processes editing /etc/hosts
    if lsof /etc/hosts 2>/dev/null | grep -q "hosts"; then
        editors=$(lsof /etc/hosts 2>/dev/null | tail -n +2 | awk '{print $1, $2}')
        if [[ -n "$editors" ]]; then
            echo "$editors" | while read -r proc pid; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Process editing /etc/hosts: $proc (PID:$pid)" >> "$LOG_FILE"
            done
        fi
    fi

    # Monitor /etc/resolv.conf as well (DNS resolution)
    if [[ -f /etc/resolv.conf ]]; then
        resolv_mtime=$(stat -c %Y /etc/resolv.conf 2>/dev/null)
        if [[ -n "${RESOLV_MTIME:-}" && "$resolv_mtime" != "$RESOLV_MTIME" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] /etc/resolv.conf modified" >> "$LOG_FILE"
            nameservers=$(grep "^nameserver" /etc/resolv.conf 2>/dev/null)
            if [[ -n "$nameservers" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] DNS servers: $nameservers" >> "$LOG_FILE"
            fi
        fi
        RESOLV_MTIME="$resolv_mtime"
    fi

    sleep 3
done
