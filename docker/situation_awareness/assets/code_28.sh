#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/memory_usage.log"
echo "$(date) [INFO] Memory Monitor Started" >> "$LOG_FILE"

# Track previous kcore access time
KCORE_PREV=""
PROC_MEM_PREV=""

while true; do
    # Monitor memory usage > 90%
    mem_usage=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if [[ $mem_usage -gt 90 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] High memory usage detected: ${mem_usage}%" >> "$LOG_FILE"
    fi

    # Monitor /proc/kcore access (memory dump attempts)
    if [[ -f /proc/kcore ]]; then
        kcore_time=$(stat -c %Y /proc/kcore 2>/dev/null || echo "0")
        if [[ -n "$KCORE_PREV" && "$kcore_time" != "$KCORE_PREV" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] /proc/kcore access detected - possible memory dump" >> "$LOG_FILE"
        fi
        KCORE_PREV="$kcore_time"
    fi

    # Monitor /proc/[pid]/mem access attempts
    for mem_file in /proc/[0-9]*/mem; do
        if [[ -f "$mem_file" ]]; then
            mem_time=$(stat -c %Y "$mem_file" 2>/dev/null || echo "0")
            mem_key="${mem_file}_${mem_time}"
            if [[ ! "$PROC_MEM_PREV" =~ "$mem_key" ]]; then
                pid=$(echo "$mem_file" | grep -oP '\d+')
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Process memory access: PID=$pid CMD=$cmd" >> "$LOG_FILE"
            fi
        fi
    done 2>/dev/null

    # Monitor swap creation
    swap_count=$(swapon -s | tail -n +2 | wc -l)
    if [[ $swap_count -gt 0 ]]; then
        swap_info=$(swapon -s | tail -n +2)
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Swap space active: $swap_count swap(s)" >> "$LOG_FILE"
    fi

    # Note: tmpfs/ramfs monitoring moved to mount_monitor.sh to avoid duplication

    sleep 3
done
