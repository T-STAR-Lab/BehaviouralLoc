#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/capability_monitor.log"
echo "$(date) [INFO] Linux Capabilities Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor processes with capabilities
    for pid_dir in /proc/[0-9]*/status; do
        if [[ -f "$pid_dir" ]]; then
            pid=$(echo "$pid_dir" | grep -oP '\d+')

            # Get effective capabilities
            cap_eff=$(grep "^CapEff:" "$pid_dir" 2>/dev/null | awk '{print $2}')

            # Check for non-zero capabilities (excluding common system processes)
            if [[ -n "$cap_eff" && "$cap_eff" != "0000000000000000" ]]; then
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")

                # Skip common privileged processes
                if ! echo "$cmd" | grep -qE "systemd|dbus|NetworkManager|avahi"; then
                    if [[ ! -f "/tmp/cap_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Process with capabilities: PID=$pid CapEff=$cap_eff CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/cap_${pid}"
                    fi
                fi

                # Alert on dangerous capabilities
                cap_value=$((16#$cap_eff))

                # CAP_SYS_ADMIN = bit 21 (very powerful)
                if [[ $(( (cap_value >> 21) & 1 )) -eq 1 ]]; then
                    if [[ ! -f "/tmp/cap_admin_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] CAP_SYS_ADMIN capability: PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/cap_admin_${pid}"
                    fi
                fi

                # CAP_NET_RAW = bit 13 (packet sniffing)
                if [[ $(( (cap_value >> 13) & 1 )) -eq 1 ]]; then
                    if [[ ! -f "/tmp/cap_netraw_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] CAP_NET_RAW capability: PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/cap_netraw_${pid}"
                    fi
                fi

                # CAP_DAC_OVERRIDE = bit 1 (bypass file permissions)
                if [[ $(( (cap_value >> 1) & 1 )) -eq 1 ]]; then
                    if [[ ! -f "/tmp/cap_dac_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] CAP_DAC_OVERRIDE capability: PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/cap_dac_${pid}"
                    fi
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor setcap/getcap commands
    if ps aux | grep -v grep | grep -qE "setcap|getcap"; then
        cap_cmds=$(ps aux | grep -v grep | grep -E "setcap|getcap" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Capability modification: $cap_cmds" >> "$LOG_FILE"
    fi

    # Monitor files with capabilities
    if command -v getcap >/dev/null 2>&1; then
        cap_files=$(find /usr/bin /usr/sbin /bin /sbin -type f -exec getcap {} \; 2>/dev/null | grep "=")
        if [[ -n "$cap_files" ]]; then
            echo "$cap_files" | while read -r line; do
                file=$(echo "$line" | awk '{print $1}')
                if [[ ! -f "/tmp/cap_file_$(basename "$file")" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] File with capabilities: $line" >> "$LOG_FILE"
                    touch "/tmp/cap_file_$(basename "$file")"
                fi
            done
        fi
    fi

    # Clean up old markers
    find /tmp -name "cap_*" -mmin +30 -delete 2>/dev/null

    sleep 5
done
