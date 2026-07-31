#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/mount_monitor.log"
echo "$(date) [INFO] Mount Monitor Started" >> "$LOG_FILE"

# Store initial mount state
MOUNT_HASH=$(cat /proc/mounts | md5sum | awk '{print $1}')

while true; do
    # Monitor mount changes
    current_hash=$(cat /proc/mounts | md5sum | awk '{print $1}')

    if [[ "$current_hash" != "$MOUNT_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Filesystem mount/unmount detected!" >> "$LOG_FILE"

        # Find new mounts
        comm -13 <(echo "$MOUNT_HASH") <(echo "$current_hash") 2>/dev/null || true

        MOUNT_HASH="$current_hash"

        # Log current mounts
        cat /proc/mounts | while read -r line; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Mount: $line" >> "$LOG_FILE"
        done
    fi

    # Monitor tmpfs/ramfs mounts (memory-backed filesystems)
    tmpfs_mounts=$(mount | grep -E "tmpfs|ramfs" | grep -v "/sys\|/run\|/dev")
    if [[ -n "$tmpfs_mounts" ]]; then
        echo "$tmpfs_mounts" | while read -r line; do
            mount_point=$(echo "$line" | awk '{print $3}')
            # Check if this is a new mount
            if [[ ! -f "/tmp/mount_seen_${mount_point//\//_}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Memory-backed filesystem mounted: $line" >> "$LOG_FILE"
                touch "/tmp/mount_seen_${mount_point//\//_}"
            fi
        done
    fi

    # Monitor mount/umount commands
    if ps aux | grep -v grep | grep -qE " mount | umount "; then
        mount_cmds=$(ps aux | grep -v grep | grep -E " mount | umount " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$mount_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Mount command: $mount_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor suspicious mount options
    suspicious_mounts=$(mount | grep -E "noexec|nosuid" | grep -v "noexec\|nosuid")
    if mount | grep -vE "noexec|nosuid" | grep -q "/tmp\|/dev/shm"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Suspicious mount without security flags on /tmp or /dev/shm" >> "$LOG_FILE"
    fi

    # Monitor bind mounts (can be used for privilege escalation)
    bind_mounts=$(mount | grep "bind")
    if [[ -n "$bind_mounts" ]]; then
        echo "$bind_mounts" | while read -r line; do
            if [[ ! -f "/tmp/bind_seen_$(echo "$line" | md5sum | awk '{print $1}')" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Bind mount detected: $line" >> "$LOG_FILE"
                touch "/tmp/bind_seen_$(echo "$line" | md5sum | awk '{print $1}')"
            fi
        done
    fi

    # Monitor overlay filesystems (common in containers)
    overlay_mounts=$(mount | grep "overlay")
    if [[ -n "$overlay_mounts" ]]; then
        echo "$overlay_mounts" | while read -r line; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Overlay mount: $line" >> "$LOG_FILE"
        done
    fi

    sleep 5
done
