#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/forkbomb_detect.log"
echo "$(date) [INFO] Fork Bomb Detector Started" >> "$LOG_FILE"

# Track process counts per UID
declare -A PREV_PROC_COUNT

while true; do
    # Count processes per UID
    for uid in $(ps -eo uid | tail -n +2 | sort -u); do
        proc_count=$(ps -u "$uid" --no-headers | wc -l)

        # Get previous count
        prev_count=${PREV_PROC_COUNT[$uid]:-0}

        # Calculate rate of increase
        if [[ $prev_count -gt 0 ]]; then
            diff=$((proc_count - prev_count))

            # Alert if rapid process creation (>50 new processes in 2 seconds)
            if [[ $diff -gt 50 ]]; then
                username=$(id -nu "$uid" 2>/dev/null || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Rapid process creation detected! UID=$uid ($username): $diff new processes" >> "$LOG_FILE"
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Total processes for UID $uid: $proc_count" >> "$LOG_FILE"

                # Sample some of the processes
                sample_procs=$(ps -u "$uid" -o pid,comm --no-headers | tail -10)
                echo "$sample_procs" | while read -r pid comm; do
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Sample process: PID=$pid CMD=$comm" >> "$LOG_FILE"
                done
            fi
        fi

        # Alert if absolute count is very high
        if [[ $proc_count -gt 1000 ]]; then
            username=$(id -nu "$uid" 2>/dev/null || echo "unknown")
            if [[ ! -f "/tmp/forkbomb_${uid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Excessive processes for UID=$uid ($username): $proc_count" >> "$LOG_FILE"
                touch "/tmp/forkbomb_${uid}"
            fi
        fi

        PREV_PROC_COUNT[$uid]=$proc_count
    done

    # Check for specific fork bomb patterns
    if ps aux | awk '{print $11}' | sort | uniq -c | sort -rn | awk '$1 > 100 {print $2}' | head -1 | grep -q "."; then
        fork_cmd=$(ps aux | awk '{print $11}' | sort | uniq -c | sort -rn | head -1)
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Potential fork bomb pattern: $fork_cmd" >> "$LOG_FILE"
    fi

    # Monitor total process count
    total_procs=$(ps aux --no-headers | wc -l)
    if [[ $total_procs -gt 5000 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] System-wide process count very high: $total_procs" >> "$LOG_FILE"
    fi

    # Check process limits
    if [[ -r /proc/sys/kernel/pid_max ]]; then
        pid_max=$(cat /proc/sys/kernel/pid_max)
        pid_usage=$((total_procs * 100 / pid_max))
        if [[ $pid_usage -gt 80 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] PID space usage: ${pid_usage}% ($total_procs/$pid_max)" >> "$LOG_FILE"
        fi
    fi

    # Clean up old markers
    find /tmp -name "forkbomb_*" -mmin +5 -delete 2>/dev/null

    sleep 2
done
