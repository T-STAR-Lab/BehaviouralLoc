#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/systemd_monitor.log"
echo "$(date) [INFO] Systemd Monitor Started" >> "$LOG_FILE"

# Store initial systemd unit state
SYSTEMD_HASH=$(find /etc/systemd/system /usr/lib/systemd/system -type f 2>/dev/null | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')

while true; do
    # Monitor systemd unit file changes
    current_hash=$(find /etc/systemd/system /usr/lib/systemd/system -type f 2>/dev/null | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')

    if [[ "$current_hash" != "$SYSTEMD_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Systemd unit files modified!" >> "$LOG_FILE"

        # Find which files changed
        find /etc/systemd/system /usr/lib/systemd/system -type f -mmin -1 2>/dev/null | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Modified unit: $file" >> "$LOG_FILE"
        done

        SYSTEMD_HASH="$current_hash"
    fi

    # Monitor systemctl commands
    if ps aux | grep -v grep | grep -qE "systemctl"; then
        systemctl_cmds=$(ps aux | grep -v grep | grep "systemctl" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$systemctl_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Systemctl command: $systemctl_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor new/enabled services
    if command -v systemctl >/dev/null 2>&1; then
        enabled_services=$(systemctl list-unit-files --state=enabled --no-pager --no-legend 2>/dev/null | wc -l)
        if [[ -n "${PREV_ENABLED:-}" && $enabled_services -ne $PREV_ENABLED ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Number of enabled services changed: $PREV_ENABLED -> $enabled_services" >> "$LOG_FILE"
        fi
        PREV_ENABLED=$enabled_services

        # Check for failed services
        failed_services=$(systemctl list-units --state=failed --no-pager --no-legend 2>/dev/null)
        if [[ -n "$failed_services" ]]; then
            echo "$failed_services" | while read -r line; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Failed service: $line" >> "$LOG_FILE"
            done
        fi
    fi

    # Monitor for suspicious systemd unit content
    suspicious_patterns="curl|wget|nc|bash -c|python -c|/dev/tcp"
    if grep -rE "$suspicious_patterns" /etc/systemd/system/*.service 2>/dev/null | grep -v "^Binary"; then
        matches=$(grep -rE "$suspicious_patterns" /etc/systemd/system/*.service 2>/dev/null | grep -v "^Binary" | head -3)
        if [[ -n "$matches" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Suspicious systemd unit content!" >> "$LOG_FILE"
            echo "$matches" | while read -r line; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Suspicious: $line" >> "$LOG_FILE"
            done
        fi
    fi

    # Monitor systemd daemon-reload
    if ps aux | grep -v grep | grep -qE "systemd.*daemon-reload"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Systemd daemon reload detected" >> "$LOG_FILE"
    fi

    sleep 5
done
