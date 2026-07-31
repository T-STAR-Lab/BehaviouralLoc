#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/proc_watchdog.log"
echo "$(date) [INFO] Process Watchdog Started" >> "$LOG_FILE"

# Processes to monitor (can be configured)
# Format: "process_name:restart_command"
WATCHED_PROCS=(
    "worker:/usr/bin/worker"
    "sshd:/usr/sbin/sshd"
    "nginx:/usr/sbin/nginx"
    "apache2:/usr/sbin/apache2"
    "mysql:/usr/sbin/mysqld"
)

# Track process states
declare -A PROC_STATE

while true; do
    for watch_spec in "${WATCHED_PROCS[@]}"; do
        proc_name="${watch_spec%%:*}"
        restart_cmd="${watch_spec##*:}"

        # Check if process is running
        if ps aux | grep -v grep | grep -q "$proc_name"; then
            # Process is running
            if [[ "${PROC_STATE[$proc_name]:-running}" == "dead" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Process recovered: $proc_name" >> "$LOG_FILE"
                PROC_STATE[$proc_name]="running"
            fi
        else
            # Process is not running
            if [[ "${PROC_STATE[$proc_name]:-unknown}" != "dead" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Process terminated: $proc_name" >> "$LOG_FILE"
                PROC_STATE[$proc_name]="dead"

                # Attempt to restart (if restart command is valid)
                if [[ -n "$restart_cmd" && -x "$restart_cmd" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Attempting to restart $proc_name..." >> "$LOG_FILE"
                    $restart_cmd >> "$LOG_FILE" 2>&1 &
                    restart_pid=$!
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Restart initiated for $proc_name (PID: $restart_pid)" >> "$LOG_FILE"
                fi
            fi
        fi
    done

    # Monitor for kill attempts on watched processes
    running_kills=$(ps aux | grep -v grep | grep -E "kill.*worker|kill.*sshd|kill.*nginx|kill.*apache|kill.*mysql" 2>/dev/null)
    if [[ -n "$running_kills" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Kill command detected on monitored process: $running_kills" >> "$LOG_FILE"
    fi

    # Monitor for pkill/killall on watched processes
    if ps aux | grep -v grep | grep -qE "pkill|killall"; then
        pkill_cmds=$(ps aux | grep -v grep | grep -E "pkill|killall" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Mass kill command detected: $pkill_cmds" >> "$LOG_FILE"
    fi

    # Monitor for systemctl stop on watched services
    if ps aux | grep -v grep | grep -q "systemctl stop"; then
        stop_cmds=$(ps aux | grep -v grep | grep "systemctl stop" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Service stop command: $stop_cmds" >> "$LOG_FILE"
    fi

    sleep 3
done
