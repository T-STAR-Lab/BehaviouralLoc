#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/ssh_monitor.log"
echo "$(date) [INFO] SSH Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor SSH connections
    ssh_conns=$(ss -tn state established '( dport = :22 or sport = :22 )' 2>/dev/null | tail -n +2)
    if [[ -n "$ssh_conns" ]]; then
        echo "$ssh_conns" | while read -r line; do
            remote_ip=$(echo "$line" | awk '{print $4}' | cut -d: -f1)
            if [[ ! -f "/tmp/ssh_conn_${remote_ip//[.:]/}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] SSH connection: $line" >> "$LOG_FILE"
                touch "/tmp/ssh_conn_${remote_ip//[.:]/}"
            fi
        done
    fi

    # Monitor SSH tunnel creation (-L, -R, -D flags)
    if ps aux | grep -v grep | grep -E "ssh.*-[LRD]"; then
        tunnels=$(ps aux | grep -v grep | grep -E "ssh.*-[LRD]" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] SSH tunnel detected: $tunnels" >> "$LOG_FILE"
    fi

    # Monitor sshd on non-standard ports
    sshd_ports=$(ss -tuln | grep -E "sshd|:22 " | grep -v ":22 " | awk '{print $5}')
    if [[ -n "$sshd_ports" ]]; then
        echo "$sshd_ports" | while read -r port; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] SSH on non-standard port: $port" >> "$LOG_FILE"
        done
    fi

    # Monitor SSH key operations
    if ps aux | grep -v grep | grep -qE "ssh-keygen|ssh-copy-id"; then
        key_ops=$(ps aux | grep -v grep | grep -E "ssh-keygen|ssh-copy-id" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] SSH key operation: $key_ops" >> "$LOG_FILE"
    fi

    # Monitor ~/.ssh directory changes
    for home_dir in /home/*; do
        if [[ -d "$home_dir/.ssh" ]]; then
            ssh_changes=$(find "$home_dir/.ssh" -type f -mmin -1 2>/dev/null)
            if [[ -n "$ssh_changes" ]]; then
                echo "$ssh_changes" | while read -r file; do
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] SSH config modified: $file" >> "$LOG_FILE"
                done
            fi
        fi
    done

    # Monitor failed SSH attempts (if auth.log accessible)
    if [[ -r /var/log/auth.log ]]; then
        failed_ssh=$(tail -20 /var/log/auth.log 2>/dev/null | grep "Failed password" | tail -5)
        if [[ -n "$failed_ssh" ]]; then
            echo "$failed_ssh" | while read -r line; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Failed SSH: $line" >> "$LOG_FILE"
            done
        fi
    fi

    # Monitor SSH agent forwarding
    if ps aux | grep -v grep | grep -E "ssh.*-A"; then
        agent_fwd=$(ps aux | grep -v grep | grep -E "ssh.*-A" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] SSH agent forwarding: $agent_fwd" >> "$LOG_FILE"
    fi

    # Clean up old connection markers
    find /tmp -name "ssh_conn_*" -mmin +60 -delete 2>/dev/null

    sleep 3
done
