#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/time_monitor.log"
echo "$(date) [INFO] Time Monitor Started" >> "$LOG_FILE"

# Store initial time
PREV_TIME=$(date +%s)

while true; do
    # Check current time and hour
    current_hour=$(date +%H)
    current_day=$(date +%u)  # 1=Monday, 7=Sunday

    # Monitor off-hours activity (weekends or after-hours)
    if [[ $current_day -ge 6 ]] || [[ $current_hour -lt 6 ]] || [[ $current_hour -gt 22 ]]; then
        # Check for suspicious activity during off-hours
        active_users=$(who | wc -l)
        if [[ $active_users -gt 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Off-hours activity detected: $active_users user(s)" >> "$LOG_FILE"
        fi

        # Log active processes during off-hours
        user_procs=$(ps aux | grep -v "root" | grep -v "^USER" | wc -l)
        if [[ $user_procs -gt 5 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Off-hours: $user_procs non-root processes" >> "$LOG_FILE"
        fi
    fi

    # Monitor system clock changes
    current_time=$(date +%s)
    time_diff=$((current_time - PREV_TIME))

    # Alert if time jumped more than expected (adjusted clock)
    if [[ $time_diff -lt 0 ]] || [[ $time_diff -gt 10 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] System clock anomaly detected! Time jumped ${time_diff}s" >> "$LOG_FILE"
    fi
    PREV_TIME=$current_time

    # Monitor date/timedatectl commands
    if ps aux | grep -v grep | grep -qE " date |timedatectl"; then
        time_cmds=$(ps aux | grep -v grep | grep -E " date |timedatectl" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Time modification command: $time_cmds" >> "$LOG_FILE"
    fi

    # Monitor NTP synchronization status
    if command -v timedatectl >/dev/null 2>&1; then
        ntp_sync=$(timedatectl status 2>/dev/null | grep "System clock synchronized" | awk '{print $4}')
        if [[ "$ntp_sync" == "no" ]]; then
            if [[ ! -f /tmp/ntp_nosync_logged ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] NTP synchronization disabled" >> "$LOG_FILE"
                touch /tmp/ntp_nosync_logged
            fi
        fi
    fi

    # Monitor for time-based evasion (rapid process execution)
    rapid_procs=$(ps aux | awk -v now="$(date +%s)" '$9 ~ /^[0-9][0-9]:[0-9][0-9]$/ {print $11}' | wc -l)
    if [[ $rapid_procs -gt 10 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Multiple recent processes: $rapid_procs" >> "$LOG_FILE"
    fi

    # Check for backdated files (files with future timestamps)
    future_files=$(find /tmp /var/tmp -type f -newermt "$(date -d '+1 hour' '+%Y-%m-%d %H:%M:%S')" 2>/dev/null | head -5)
    if [[ -n "$future_files" ]]; then
        echo "$future_files" | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] File with future timestamp: $file" >> "$LOG_FILE"
        done
    fi

    sleep 5
done
