#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/port_monitor.log"
echo "$(date) [INFO] Port Monitor Started" >> "$LOG_FILE"

# Store initial listening ports
PORTS_BASELINE=$(ss -tuln | sort)

while true; do
    # Monitor listening ports
    current_ports=$(ss -tuln | sort)

    # Detect new listening ports
    new_ports=$(comm -13 <(echo "$PORTS_BASELINE") <(echo "$current_ports") | grep -v "^State")
    if [[ -n "$new_ports" ]]; then
        echo "$new_ports" | while read -r line; do
            port=$(echo "$line" | awk '{print $5}' | grep -oP ':\K\d+$')
            if [[ -n "$port" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] New listening port: $line" >> "$LOG_FILE"
            fi
        done
        PORTS_BASELINE="$current_ports"
    fi

    # Monitor privileged ports (< 1024)
    priv_ports=$(ss -tuln | awk '{print $5}' | grep -oP ':\K\d+$' | awk '$1 < 1024 && $1 > 0')
    if [[ -n "$priv_ports" ]]; then
        echo "$priv_ports" | while read -r port; do
            # Find process using this port
            proc=$(ss -tulnp | grep ":$port " | grep -oP 'users:\(\("[^"]+",pid=\K\d+' | head -1)
            if [[ -n "$proc" ]]; then
                cmd=$(ps -p "$proc" -o comm= 2>/dev/null || echo "unknown")
                if [[ ! -f "/tmp/privport_${port}_seen" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Privileged port $port: $cmd (PID:$proc)" >> "$LOG_FILE"
                    touch "/tmp/privport_${port}_seen"
                fi
            fi
        done
    fi

    # Detect port scanning (rapid connection attempts)
    if [[ -f /proc/net/tcp ]]; then
        syn_recv=$(netstat -tan 2>/dev/null | grep SYN_RECV | wc -l)
        if [[ $syn_recv -gt 20 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Possible port scan - $syn_recv SYN_RECV connections" >> "$LOG_FILE"
        fi
    fi

    # Monitor suspicious high ports (common for reverse shells)
    high_ports=$(ss -tn state established | awk '{print $4}' | grep -oP ':\K\d+$' | awk '$1 > 40000')
    if [[ -n "$high_ports" ]]; then
        high_port_count=$(echo "$high_ports" | wc -l)
        if [[ $high_port_count -gt 10 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Multiple high port connections: $high_port_count" >> "$LOG_FILE"
        fi
    fi

    # Monitor well-known service ports
    service_ports="21 23 25 53 80 443 3306 5432 6379 27017"
    for port in $service_ports; do
        if ss -tuln | grep -q ":$port "; then
            proc=$(ss -tulnp | grep ":$port " | grep -oP 'users:\(\("[^"]+",pid=\K\d+' | head -1)
            if [[ -n "$proc" && ! -f "/tmp/service_${port}_logged" ]]; then
                cmd=$(ps -p "$proc" -o comm= 2>/dev/null || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Service on port $port: $cmd" >> "$LOG_FILE"
                touch "/tmp/service_${port}_logged"
            fi
        fi
    done

    # Monitor nc/ncat/socat (often used for port binding)
    if ps aux | grep -v grep | grep -qE "nc|ncat|socat.*LISTEN"; then
        netcat=$(ps aux | grep -v grep | grep -E "nc|ncat|socat.*LISTEN" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Network listener detected: $netcat" >> "$LOG_FILE"
    fi

    # Clean up old markers
    find /tmp -name "privport_*_seen" -mmin +120 -delete 2>/dev/null
    find /tmp -name "service_*_logged" -mmin +120 -delete 2>/dev/null

    sleep 3
done
