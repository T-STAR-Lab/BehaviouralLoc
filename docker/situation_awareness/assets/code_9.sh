#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/covert_channel.log"
echo "$(date) [INFO] Covert Channel Detector Started" >> "$LOG_FILE"

# Track timing patterns
PREV_NET_BYTES=0
PREV_TIME=$(date +%s%N)

while true; do
    # Monitor timing anomalies in network traffic
    if [[ -f /proc/net/dev ]]; then
        # Get total network bytes
        net_bytes=$(awk '{if(NR>2) {rx+=$2; tx+=$10}} END {print rx+tx}' /proc/net/dev)
        current_time=$(date +%s%N)

        if [[ $PREV_NET_BYTES -gt 0 ]]; then
            # Calculate bytes per nanosecond
            time_diff=$((current_time - PREV_TIME))
            byte_diff=$((net_bytes - PREV_NET_BYTES))

            # Very small, regular data transfers (covert channel indicator)
            if [[ $byte_diff -gt 0 && $byte_diff -lt 1000 ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Small network transfer: ${byte_diff} bytes" >> "$LOG_FILE"
            fi
        fi

        PREV_NET_BYTES=$net_bytes
        PREV_TIME=$current_time
    fi

    # Monitor ICMP traffic (often used for covert channels)
    if [[ -r /proc/net/icmp ]]; then
        icmp_packets=$(cat /proc/net/icmp 2>/dev/null | wc -l)
        if [[ $icmp_packets -gt 5 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Active ICMP traffic: $icmp_packets entries" >> "$LOG_FILE"
        fi
    fi

    # Monitor DNS traffic patterns (DNS tunneling)
    dns_procs=$(ps aux | grep -v grep | grep -E "dig|nslookup|host" | wc -l)
    if [[ $dns_procs -gt 3 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Multiple DNS queries: $dns_procs processes" >> "$LOG_FILE"
    fi

    # Monitor file access timing patterns
    if [[ -d /tmp ]]; then
        # Look for files being accessed in rapid succession
        recent_access=$(find /tmp -type f -amin -1 2>/dev/null | wc -l)
        if [[ $recent_access -gt 20 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] High file access rate in /tmp: $recent_access files" >> "$LOG_FILE"
        fi
    fi

    # Monitor CPU timing attacks
    cpu_samples=0
    for i in {1..3}; do
        cpu_idle=$(top -bn1 | grep "Cpu(s)" | awk '{print $8}' | cut -d'%' -f1)
        if [[ -n "$cpu_idle" ]]; then
            cpu_busy=$(echo "100 - $cpu_idle" | bc 2>/dev/null || echo "0")
            if [[ "${cpu_busy%.*}" -gt 95 ]]; then
                cpu_samples=$((cpu_samples + 1))
            fi
        fi
        sleep 0.1
    done

    if [[ $cpu_samples -eq 3 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Sustained high CPU usage - possible timing channel" >> "$LOG_FILE"
    fi

    # Monitor processes with unusual I/O patterns
    high_io=$(ps aux | sort -k6 -rn | head -5 | awk '$6 > 1000 {print $2, $11, $6}')
    if [[ -n "$high_io" ]]; then
        echo "$high_io" | while read -r pid cmd mem; do
            if [[ ! -f "/tmp/highio_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] High I/O process: PID=$pid MEM=${mem}KB CMD=$cmd" >> "$LOG_FILE"
                touch "/tmp/highio_${pid}"
            fi
        done
    fi

    # Monitor steganography tools
    if ps aux | grep -v grep | grep -qE "steghide|outguess|stegsnow"; then
        steg_tools=$(ps aux | grep -v grep | grep -E "steghide|outguess|stegsnow" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Steganography tool detected: $steg_tools" >> "$LOG_FILE"
    fi

    # Clean up old markers
    find /tmp -name "highio_*" -mmin +5 -delete 2>/dev/null

    sleep 5
done
