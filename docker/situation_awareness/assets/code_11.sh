#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/cron_changes.log"
echo "$(date) [INFO] Cron Monitor Started" >> "$LOG_FILE"

# Store initial cron state
CRON_HASH=$(find /var/spool/cron /etc/cron* -type f 2>/dev/null | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')

while true; do
    # Monitor crontab changes
    current_hash=$(find /var/spool/cron /etc/cron* -type f 2>/dev/null | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')

    if [[ "$current_hash" != "$CRON_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Cron configuration changed!" >> "$LOG_FILE"

        # Find which cron file changed
        find /var/spool/cron /etc/cron* -type f -mmin -1 2>/dev/null | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Modified cron file: $file" >> "$LOG_FILE"
        done

        CRON_HASH="$current_hash"
    fi

    # Monitor crontab command usage
    if ps aux | grep -v grep | grep -qE "crontab|cron"; then
        cron_cmds=$(ps aux | grep -v grep | grep -E "crontab" | grep -v "/usr/sbin/cron" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$cron_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Crontab command detected: $cron_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor systemd timers (modern cron alternative)
    if command -v systemctl >/dev/null 2>&1; then
        active_timers=$(systemctl list-timers --no-pager --no-legend 2>/dev/null | wc -l)
        if [[ $active_timers -gt 0 ]]; then
            new_timers=$(systemctl list-timers --no-pager --no-legend 2>/dev/null | grep -v "apt-daily\|fwupd\|motd" | head -3)
            if [[ -n "$new_timers" ]]; then
                echo "$new_timers" | while read -r line; do
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Active systemd timer: $line" >> "$LOG_FILE"
                done
            fi
        fi
    fi

    # Check for suspicious cron entries
    suspicious_patterns="curl|wget|nc|bash -i|python -c|perl -e|/dev/tcp"
    if grep -rE "$suspicious_patterns" /etc/cron* /var/spool/cron 2>/dev/null | grep -v "^Binary"; then
        matches=$(grep -rE "$suspicious_patterns" /etc/cron* /var/spool/cron 2>/dev/null | grep -v "^Binary" | head -3)
        if [[ -n "$matches" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Suspicious cron entry detected!" >> "$LOG_FILE"
            echo "$matches" | while read -r line; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] $line" >> "$LOG_FILE"
            done
        fi
    fi

    sleep 5
done
