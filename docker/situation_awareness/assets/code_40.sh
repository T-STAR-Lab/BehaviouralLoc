#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/signal_monitor.log"
echo "$(date) [INFO] Signal Handler Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor signal handlers for all processes
    for pid_dir in /proc/[0-9]*/status; do
        if [[ -f "$pid_dir" ]]; then
            pid=$(echo "$pid_dir" | grep -oP '\d+')

            # Get signal masks
            sig_ign=$(grep "^SigIgn:" "$pid_dir" 2>/dev/null | awk '{print $2}')
            sig_cgt=$(grep "^SigCgt:" "$pid_dir" 2>/dev/null | awk '{print $2}')

            # Check for processes ignoring critical signals (SIGTERM, SIGINT)
            # SIGTERM=15 (bit 14), SIGINT=2 (bit 1)
            if [[ -n "$sig_ign" && "$sig_ign" != "0000000000000000" ]]; then
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                if [[ ! -f "/tmp/sigign_${pid}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Process ignoring signals: PID=$pid SigIgn=$sig_ign CMD=$cmd" >> "$LOG_FILE"
                    touch "/tmp/sigign_${pid}"
                fi
            fi

            # Check for unusual signal handlers
            if [[ -n "$sig_cgt" && "$sig_cgt" != "0000000000000000" ]]; then
                # Convert hex to see if catching unusual signals
                sig_value=$((16#$sig_cgt))
                if [[ $sig_value -gt 1000000 ]]; then
                    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                    if [[ ! -f "/tmp/sigcgt_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Custom signal handlers: PID=$pid SigCgt=$sig_cgt CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/sigcgt_${pid}"
                    fi
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor trap/signal commands in shells
    if ps aux | grep -v grep | grep -qE "trap|kill -"; then
        signal_cmds=$(ps aux | grep -v grep | grep -E "trap|kill -" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Signal command: $signal_cmds" >> "$LOG_FILE"
    fi

    # Monitor processes that are uninterruptible (D state)
    uninterruptible=$(ps aux | awk '$8 == "D" {print $2, $11}')
    if [[ -n "$uninterruptible" ]]; then
        echo "$uninterruptible" | while read -r pid cmd; do
            if [[ ! -f "/tmp/unint_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Uninterruptible process: PID=$pid CMD=$cmd" >> "$LOG_FILE"
                touch "/tmp/unint_${pid}"
            fi
        done
    fi

    # Monitor zombie processes (might indicate signal handling issues)
    zombies=$(ps aux | awk '$8 == "Z" {print $2, $11}')
    if [[ -n "$zombies" ]]; then
        zombie_count=$(echo "$zombies" | wc -l)
        if [[ $zombie_count -gt 5 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Multiple zombie processes: $zombie_count" >> "$LOG_FILE"
        fi
    fi

    # Clean up old markers
    find /tmp -name "sigign_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "sigcgt_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "unint_*" -mmin +2 -delete 2>/dev/null

    sleep 3
done
