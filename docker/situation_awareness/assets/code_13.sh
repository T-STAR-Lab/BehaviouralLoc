#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/disk_usage.log"
echo "$(date) [INFO] Disk Monitor Started" >> "$LOG_FILE"

# Store previous disk read bytes
PREV_READ_BYTES=""

while true; do
    # Monitor disk space thresholds
    df -h | tail -n +2 | while read -r line; do
        usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
        mount=$(echo "$line" | awk '{print $6}')
        if [[ $usage -gt 90 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Disk usage critical: $mount at ${usage}%" >> "$LOG_FILE"
        elif [[ $usage -gt 80 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Disk usage high: $mount at ${usage}%" >> "$LOG_FILE"
        fi
    done

    # Monitor bulk read operations (potential data exfiltration)
    if [[ -f /proc/diskstats ]]; then
        total_reads=0
        while read -r line; do
            # Field 6 is sectors read
            reads=$(echo "$line" | awk '{print $6}')
            total_reads=$((total_reads + reads))
        done < /proc/diskstats

        if [[ -n "$PREV_READ_BYTES" ]]; then
            read_diff=$((total_reads - PREV_READ_BYTES))
            # Alert if > 100MB read in 5 seconds (suspicious bulk read)
            threshold=204800  # 100MB in 512-byte sectors
            if [[ $read_diff -gt $threshold ]]; then
                mb_read=$((read_diff / 2048))
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Bulk disk read detected: ${mb_read}MB in 5s" >> "$LOG_FILE"
            fi
        fi
        PREV_READ_BYTES=$total_reads
    fi

    # Monitor for large file operations
    if command -v lsof >/dev/null 2>&1; then
        large_files=$(lsof 2>/dev/null | awk '$7 ~ /^[0-9]+$/ && $7 > 104857600 {print $1, $2, $7, $9}' | head -5)
        if [[ -n "$large_files" ]]; then
            echo "$large_files" | while read -r proc pid size file; do
                size_mb=$((size / 1048576))
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Large file access: $proc (PID:$pid) ${size_mb}MB - $file" >> "$LOG_FILE"
            done
        fi
    fi

    sleep 5
done
