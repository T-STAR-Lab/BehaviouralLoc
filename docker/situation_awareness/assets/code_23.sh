#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/ipc_monitor.log"
echo "$(date) [INFO] IPC Monitor Started" >> "$LOG_FILE"

# Store baseline IPC state
PREV_SHM_COUNT=0
PREV_MSG_COUNT=0
PREV_SEM_COUNT=0

while true; do
    # Monitor shared memory segments
    if command -v ipcs >/dev/null 2>&1; then
        shm_count=$(ipcs -m 2>/dev/null | grep -v "^--\|^key" | wc -l)
        if [[ $shm_count -gt $PREV_SHM_COUNT ]]; then
            new_shm=$(ipcs -m 2>/dev/null | tail -$((shm_count - PREV_SHM_COUNT)))
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] New shared memory segment(s) created" >> "$LOG_FILE"
            echo "$new_shm" | while read -r line; do
                if [[ "$line" != *"key"* && "$line" != *"--"* ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] SHM: $line" >> "$LOG_FILE"
                fi
            done
        fi
        PREV_SHM_COUNT=$shm_count

        # Monitor message queues
        msg_count=$(ipcs -q 2>/dev/null | grep -v "^--\|^key" | wc -l)
        if [[ $msg_count -gt $PREV_MSG_COUNT ]]; then
            new_msg=$(ipcs -q 2>/dev/null | tail -$((msg_count - PREV_MSG_COUNT)))
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] New message queue(s) created" >> "$LOG_FILE"
            echo "$new_msg" | while read -r line; do
                if [[ "$line" != *"key"* && "$line" != *"--"* ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] MSG: $line" >> "$LOG_FILE"
                fi
            done
        fi
        PREV_MSG_COUNT=$msg_count

        # Monitor semaphores
        sem_count=$(ipcs -s 2>/dev/null | grep -v "^--\|^key" | wc -l)
        if [[ $sem_count -gt $PREV_SEM_COUNT ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] New semaphore(s) created: count=$sem_count" >> "$LOG_FILE"
        fi
        PREV_SEM_COUNT=$sem_count
    fi

    # Monitor large shared memory allocations
    if [[ -d /dev/shm ]]; then
        large_shm=$(find /dev/shm -type f -size +10M 2>/dev/null)
        if [[ -n "$large_shm" ]]; then
            echo "$large_shm" | while read -r file; do
                size=$(stat -c %s "$file" 2>/dev/null || echo 0)
                size_mb=$((size / 1048576))
                if [[ ! -f "/tmp/shm_file_$(basename "$file")" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Large shared memory file: $file (${size_mb}MB)" >> "$LOG_FILE"
                    touch "/tmp/shm_file_$(basename "$file")"
                fi
            done
        fi
    fi

    # Monitor processes using IPC
    if ps aux | grep -v grep | grep -qE "ipcmk|ipcs|ipcrm"; then
        ipc_cmds=$(ps aux | grep -v grep | grep -E "ipcmk|ipcs|ipcrm" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] IPC command: $ipc_cmds" >> "$LOG_FILE"
    fi

    # Monitor POSIX message queues
    if [[ -d /dev/mqueue ]]; then
        mq_count=$(find /dev/mqueue -type f 2>/dev/null | wc -l)
        if [[ $mq_count -gt 0 ]]; then
            if [[ ! -f /tmp/mqueue_logged ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] POSIX message queues active: $mq_count" >> "$LOG_FILE"
                touch /tmp/mqueue_logged
            fi
        fi
    fi

    # Monitor Unix domain sockets
    unix_sockets=$(ss -x 2>/dev/null | grep -v "^Netid" | wc -l)
    if [[ $unix_sockets -gt 100 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] High Unix socket count: $unix_sockets" >> "$LOG_FILE"
    fi

    # Clean up old markers
    find /tmp -name "shm_file_*" -mmin +30 -delete 2>/dev/null

    sleep 5
done
