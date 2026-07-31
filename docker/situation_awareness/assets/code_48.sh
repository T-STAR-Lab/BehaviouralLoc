#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/ulimit_changes.log"
echo "$(date) [INFO] Ulimit Monitor Started" >> "$LOG_FILE"

# Store previous ulimit state for each process
declare -A PREV_LIMITS

while true; do
    # Monitor ulimit changes for all running processes
    for pid in /proc/[0-9]*; do
        if [[ -d "$pid" ]]; then
            pid_num=$(basename "$pid")
            limits_file="${pid}/limits"

            if [[ -f "$limits_file" ]]; then
                # Get current limits hash
                current_hash=$(md5sum "$limits_file" 2>/dev/null | awk '{print $1}')

                if [[ -n "$current_hash" ]]; then
                    prev_hash="${PREV_LIMITS[$pid_num]:-}"

                    # Check if limits changed
                    if [[ -n "$prev_hash" && "$prev_hash" != "$current_hash" ]]; then
                        cmd=$(cat /proc/$pid_num/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Ulimit changed for PID=$pid_num CMD=$cmd" >> "$LOG_FILE"

                        # Log specific limit changes
                        critical_limits=$(grep -E "Max open files|Max processes|Max locked memory|Max file size" "$limits_file" 2>/dev/null)
                        if [[ -n "$critical_limits" ]]; then
                            echo "$critical_limits" | while read -r line; do
                                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Limit: $line" >> "$LOG_FILE"
                            done
                        fi
                    fi

                    PREV_LIMITS[$pid_num]="$current_hash"
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor for suspicious ulimit commands
    if ps aux | grep -v grep | grep -qE "ulimit|prlimit"; then
        ulimit_cmds=$(ps aux | grep -v grep | grep -E "ulimit|prlimit" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$ulimit_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Ulimit modification command detected: $ulimit_cmds" >> "$LOG_FILE"
        fi
    fi

    # Check for processes with unusual limits
    for pid in /proc/[0-9]*/limits; do
        if [[ -f "$pid" ]]; then
            # Check for unlimited file descriptors (potential socket flood)
            max_files=$(grep "Max open files" "$pid" 2>/dev/null | awk '{print $4}')
            if [[ "$max_files" == "unlimited" ]] || [[ $max_files -gt 100000 ]]; then
                pid_num=$(echo "$pid" | grep -oP '\d+')
                cmd=$(cat /proc/$pid_num/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Unusually high file limit: PID=$pid_num LIMIT=$max_files CMD=$cmd" >> "$LOG_FILE"
            fi
        fi
    done 2>/dev/null

    # Clean up tracking for dead processes
    for pid in "${!PREV_LIMITS[@]}"; do
        if [[ ! -d "/proc/$pid" ]]; then
            unset PREV_LIMITS[$pid]
        fi
    done

    sleep 3
done
