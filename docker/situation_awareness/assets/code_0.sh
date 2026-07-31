#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/anti_debug.log"
echo "$(date) [INFO] Anti-Debug Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor ptrace usage (debugging)
    for pid_dir in /proc/[0-9]*/status; do
        if [[ -f "$pid_dir" ]]; then
            pid=$(echo "$pid_dir" | grep -oP '\d+')
            tracer_pid=$(grep "^TracerPid:" "$pid_dir" 2>/dev/null | awk '{print $2}')

            # Alert if process is being debugged
            if [[ -n "$tracer_pid" && "$tracer_pid" != "0" ]]; then
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                tracer_cmd=$(cat /proc/$tracer_pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                if [[ ! -f "/tmp/debug_${pid}_${tracer_pid}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Process being debugged: PID=$pid CMD=$cmd by TracerPID=$tracer_pid ($tracer_cmd)" >> "$LOG_FILE"
                    touch "/tmp/debug_${pid}_${tracer_pid}"
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor debugger processes
    if ps aux | grep -v grep | grep -qE "gdb|lldb|python.*pdb"; then
        debuggers=$(ps aux | grep -v grep | grep -E "gdb|lldb|python.*pdb" | awk '{print $2, $11}')
        echo "$debuggers" | while read -r pid cmd; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Debugger detected: $cmd (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Monitor ptrace system call attempts
    if ps aux | grep -v grep | grep -qE "strace|ltrace"; then
        tracers=$(ps aux | grep -v grep | grep -E "strace|ltrace" | awk '{print $2, $11}')
        echo "$tracers" | while read -r pid cmd; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] System call tracer: $cmd (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Check for processes checking their own TracerPid (anti-debug technique)
    if lsof 2>/dev/null | grep -q "/proc/self/status"; then
        anti_debug=$(lsof 2>/dev/null | grep "/proc/self/status" | awk '{print $1, $2}')
        echo "$anti_debug" | while read -r proc pid; do
            if [[ ! -f "/tmp/antidebug_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Process checking debug status: $proc (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/antidebug_${pid}"
            fi
        done
    fi

    # Monitor /proc/[pid]/mem access (memory debugging)
    for mem_file in /proc/[0-9]*/mem; do
        if [[ -f "$mem_file" ]]; then
            if lsof "$mem_file" 2>/dev/null | grep -q "mem"; then
                pid=$(echo "$mem_file" | grep -oP '\d+')
                accessors=$(lsof "$mem_file" 2>/dev/null | tail -n +2 | awk '{print $1, $2}')
                echo "$accessors" | while read -r proc accessor_pid; do
                    if [[ "$accessor_pid" != "$pid" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Process memory access: $proc (PID:$accessor_pid) accessing PID=$pid" >> "$LOG_FILE"
                    fi
                done
            fi
        fi
    done 2>/dev/null

    # Monitor breakpoint instructions (INT3)
    if ps aux | grep -v grep | grep -qE "objdump|readelf|xxd"; then
        analysis=$(ps aux | grep -v grep | grep -E "objdump|readelf|xxd" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Binary analysis tool: $analysis" >> "$LOG_FILE"
    fi

    # Clean up old markers
    find /tmp -name "debug_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "antidebug_*" -mmin +10 -delete 2>/dev/null

    sleep 3
done
