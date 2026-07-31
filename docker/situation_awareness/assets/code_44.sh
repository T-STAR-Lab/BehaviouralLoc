#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/syscall_trace.log"
echo "$(date) [INFO] Syscall Tracer Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor strace usage
    if ps aux | grep -v grep | grep -qE "strace"; then
        strace_procs=$(ps aux | grep -v grep | grep "strace" | awk '{print $2, $11}')
        echo "$strace_procs" | while read -r pid cmd; do
            # Get traced PID if available
            traced=$(ps -p "$pid" -o args= 2>/dev/null | grep -oP '\-p \K\d+')
            if [[ -n "$traced" ]]; then
                traced_cmd=$(ps -p "$traced" -o comm= 2>/dev/null || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] strace tracing PID $traced ($traced_cmd)" >> "$LOG_FILE"
            else
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] strace running: $cmd (PID:$pid)" >> "$LOG_FILE"
            fi
        done
    fi

    # Monitor ltrace usage
    if ps aux | grep -v grep | grep -qE "ltrace"; then
        ltrace_procs=$(ps aux | grep -v grep | grep "ltrace" | awk '{print $2, $11}')
        echo "$ltrace_procs" | while read -r pid cmd; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] ltrace running: $cmd (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Monitor ptrace usage (check TracerPid in process status)
    for pid_dir in /proc/[0-9]*; do
        if [[ -f "$pid_dir/status" ]]; then
            tracer_pid=$(grep "^TracerPid:" "$pid_dir/status" 2>/dev/null | awk '{print $2}')
            if [[ -n "$tracer_pid" && "$tracer_pid" != "0" ]]; then
                pid=$(basename "$pid_dir")
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                tracer_cmd=$(cat /proc/$tracer_pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                if [[ ! -f "/tmp/traced_${pid}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Process being traced: PID=$pid CMD=$cmd by TRACER=$tracer_pid ($tracer_cmd)" >> "$LOG_FILE"
                    touch "/tmp/traced_${pid}"
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor gdb usage
    if ps aux | grep -v grep | grep -qE " gdb "; then
        gdb_procs=$(ps aux | grep -v grep | grep " gdb " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] GDB debugger running: $gdb_procs" >> "$LOG_FILE"
    fi

    # Monitor perf usage (performance monitoring/tracing)
    if ps aux | grep -v grep | grep -qE " perf "; then
        perf_procs=$(ps aux | grep -v grep | grep " perf " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Perf tool running: $perf_procs" >> "$LOG_FILE"
    fi

    # Monitor kernel tracing (ftrace)
    if [[ -d /sys/kernel/debug/tracing ]]; then
        tracing_on=$(cat /sys/kernel/debug/tracing/tracing_on 2>/dev/null || echo "0")
        if [[ "$tracing_on" == "1" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Kernel tracing enabled" >> "$LOG_FILE"
        fi
    fi

    # Clean up old markers
    find /tmp -name "traced_*" -mmin +10 -delete 2>/dev/null

    sleep 3
done
