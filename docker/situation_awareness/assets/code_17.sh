#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/env_monitor.log"
echo "$(date) [INFO] Environment Variable Monitor Started" >> "$LOG_FILE"

# Store baseline environment
declare -A PROC_ENV_HASH

while true; do
    # Monitor PATH changes in running processes
    for pid_dir in /proc/[0-9]*; do
        if [[ -f "$pid_dir/environ" ]]; then
            pid=$(basename "$pid_dir")
            path_var=$(tr '\0' '\n' < "$pid_dir/environ" 2>/dev/null | grep "^PATH=" || echo "")

            if [[ -n "$path_var" ]]; then
                # Check for suspicious PATH entries
                if echo "$path_var" | grep -qE "^PATH=\.:|/tmp|/dev/shm|~"; then
                    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                    if [[ ! -f "/tmp/susppath_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Suspicious PATH: $path_var for PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/susppath_${pid}"
                    fi
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor LD_PRELOAD usage
    for pid_dir in /proc/[0-9]*/environ; do
        if [[ -f "$pid_dir" ]]; then
            ld_preload=$(tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep "^LD_PRELOAD=" || echo "")
            if [[ -n "$ld_preload" ]]; then
                pid=$(echo "$pid_dir" | grep -oP '\d+')
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] LD_PRELOAD detected: $ld_preload for PID=$pid CMD=$cmd" >> "$LOG_FILE"
            fi

            # Monitor LD_LIBRARY_PATH
            ld_lib=$(tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep "^LD_LIBRARY_PATH=" || echo "")
            if [[ -n "$ld_lib" ]]; then
                if echo "$ld_lib" | grep -qE "/tmp|/dev/shm"; then
                    pid=$(echo "$pid_dir" | grep -oP '\d+')
                    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                    if [[ ! -f "/tmp/ldlib_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Suspicious LD_LIBRARY_PATH: $ld_lib for PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/ldlib_${pid}"
                    fi
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor export/setenv commands
    if ps aux | grep -v grep | grep -qE "export.*LD_|setenv"; then
        env_cmds=$(ps aux | grep -v grep | grep -E "export.*LD_|setenv" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Environment modification: $env_cmds" >> "$LOG_FILE"
    fi

    # Monitor for suspicious environment variables
    suspicious_vars="BASH_ENV|ENV|PROMPT_COMMAND"
    for pid_dir in /proc/[0-9]*/environ; do
        if [[ -f "$pid_dir" ]]; then
            for var in $suspicious_vars; do
                if tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep -q "^${var}="; then
                    pid=$(echo "$pid_dir" | grep -oP '\d+')
                    value=$(tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep "^${var}=")
                    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                    if [[ ! -f "/tmp/envvar_${var}_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Suspicious env var: $value for PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/envvar_${var}_${pid}"
                    fi
                fi
            done
        fi
    done 2>/dev/null

    # Clean up old markers
    find /tmp -name "susppath_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "ldlib_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "envvar_*" -mmin +10 -delete 2>/dev/null

    sleep 3
done
