#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/suid_monitor.log"
echo "$(date) [INFO] SUID/SGID Monitor Started" >> "$LOG_FILE"

# Create initial SUID/SGID file list
SUID_LIST="/tmp/suid_baseline.txt"
find / -type f \( -perm -4000 -o -perm -2000 \) -ls 2>/dev/null | sort > "$SUID_LIST"

while true; do
    # Find current SUID/SGID files
    current_list="/tmp/suid_current.txt"
    find / -type f \( -perm -4000 -o -perm -2000 \) -ls 2>/dev/null | sort > "$current_list"

    # Compare with baseline
    new_files=$(comm -13 "$SUID_LIST" "$current_list")

    if [[ -n "$new_files" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] New SUID/SGID file(s) detected!" >> "$LOG_FILE"
        echo "$new_files" | while read -r line; do
            filepath=$(echo "$line" | awk '{print $NF}')
            perms=$(echo "$line" | awk '{print $3}')
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] New SUID/SGID: $filepath (perms: $perms)" >> "$LOG_FILE"
        done

        # Update baseline
        cp "$current_list" "$SUID_LIST"
    fi

    # Monitor for suspicious SUID files
    suspicious_suid=$(find /tmp /var/tmp /dev/shm -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null)
    if [[ -n "$suspicious_suid" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] SUID/SGID file in suspicious location!" >> "$LOG_FILE"
        echo "$suspicious_suid" | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Suspicious SUID: $file" >> "$LOG_FILE"
        done
    fi

    # Monitor for chmod commands that set SUID/SGID
    if ps aux | grep -v grep | grep -qE "chmod.*(4[0-7][0-7][0-7]|[+]s)"; then
        chmod_cmds=$(ps aux | grep -v grep | grep -E "chmod.*(4[0-7][0-7][0-7]|[+]s)" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] SUID/SGID chmod command: $chmod_cmds" >> "$LOG_FILE"
    fi

    # Check for world-writable SUID files (very dangerous)
    dangerous_suid=$(find / -type f \( -perm -4000 -o -perm -2000 \) -perm -002 2>/dev/null)
    if [[ -n "$dangerous_suid" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] World-writable SUID/SGID file found!" >> "$LOG_FILE"
        echo "$dangerous_suid" | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Dangerous: $file" >> "$LOG_FILE"
        done
    fi

    rm -f "$current_list"
    sleep 10
done
