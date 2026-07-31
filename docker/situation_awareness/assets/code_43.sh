#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/symlink_monitor.log"
echo "$(date) [INFO] Symlink Monitor Started" >> "$LOG_FILE"

# Sensitive paths to monitor
SENSITIVE_PATHS="/etc /root /home /usr/bin /usr/sbin /bin /sbin"

while true; do
    # Find symlinks to sensitive paths
    for path in $SENSITIVE_PATHS; do
        if [[ -d "$path" ]]; then
            # Find recently created symlinks (in last 60 seconds)
            new_symlinks=$(find "$path" -type l -mmin -1 2>/dev/null)
            if [[ -n "$new_symlinks" ]]; then
                echo "$new_symlinks" | while read -r link; do
                    target=$(readlink -f "$link" 2>/dev/null || echo "broken")
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] New symlink: $link -> $target" >> "$LOG_FILE"
                done
            fi
        fi
    done

    # Monitor symlinks in world-writable directories (common attack vector)
    suspicious_dirs="/tmp /var/tmp /dev/shm"
    for dir in $suspicious_dirs; do
        if [[ -d "$dir" ]]; then
            symlinks=$(find "$dir" -type l 2>/dev/null)
            if [[ -n "$symlinks" ]]; then
                echo "$symlinks" | while read -r link; do
                    target=$(readlink -f "$link" 2>/dev/null || echo "broken")
                    # Alert if symlink points to sensitive locations
                    if echo "$target" | grep -qE "^/etc/|^/root/|^/home/.*/\.ssh/"; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Suspicious symlink in $dir: $link -> $target" >> "$LOG_FILE"
                    fi
                done
            fi
        fi
    done

    # Monitor for ln command usage
    if ps aux | grep -v grep | grep -qE " ln "; then
        ln_cmds=$(ps aux | grep -v grep | grep " ln " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Symlink creation command: $ln_cmds" >> "$LOG_FILE"
    fi

    # Check for broken symlinks (possible cleanup attempt)
    broken_links=$(find /tmp /var/tmp /dev/shm -type l ! -exec test -e {} \; -print 2>/dev/null)
    if [[ -n "$broken_links" ]]; then
        echo "$broken_links" | while read -r link; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Broken symlink: $link" >> "$LOG_FILE"
        done
    fi

    # Monitor symlinks to /proc (information disclosure)
    proc_symlinks=$(find /tmp /var/tmp /dev/shm -type l -exec readlink {} \; 2>/dev/null | grep "^/proc/")
    if [[ -n "$proc_symlinks" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Symlinks to /proc detected: $proc_symlinks" >> "$LOG_FILE"
    fi

    # Check for symlinks to device files
    device_symlinks=$(find /tmp /var/tmp /dev/shm -type l -exec readlink {} \; 2>/dev/null | grep "^/dev/")
    if [[ -n "$device_symlinks" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Symlinks to device files: $device_symlinks" >> "$LOG_FILE"
    fi

    sleep 5
done
