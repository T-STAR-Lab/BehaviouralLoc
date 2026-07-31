#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/pcap_detector.log"
echo "$(date) [INFO] Packet Capture Detector Started" >> "$LOG_FILE"

while true; do
    # Monitor promiscuous mode interfaces
    promisc=$(ip link show | grep -B1 "PROMISC" | grep -oP '^\d+: \K[^:]+')
    if [[ -n "$promisc" ]]; then
        echo "$promisc" | while read -r iface; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Promiscuous mode enabled on interface: $iface" >> "$LOG_FILE"
        done
    fi

    # Monitor packet capture tools
    if ps aux | grep -v grep | grep -qE "tcpdump|wireshark|tshark|dumpcap"; then
        pcap_procs=$(ps aux | grep -v grep | grep -E "tcpdump|wireshark|tshark|dumpcap" | awk '{print $2, $11}')
        echo "$pcap_procs" | while read -r pid cmd; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Packet capture tool running: $cmd (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Monitor raw socket usage (used by packet capture)
    if [[ -r /proc/net/raw ]]; then
        raw_sockets=$(grep -v "local_address" /proc/net/raw | wc -l)
        if [[ $raw_sockets -gt 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Raw sockets in use: $raw_sockets" >> "$LOG_FILE"
        fi
    fi

    # Monitor pcap file creation
    pcap_files=$(find /tmp /var/tmp /home -name "*.pcap" -o -name "*.pcapng" -mmin -5 2>/dev/null)
    if [[ -n "$pcap_files" ]]; then
        echo "$pcap_files" | while read -r file; do
            size=$(stat -c %s "$file" 2>/dev/null || echo 0)
            size_mb=$((size / 1048576))
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Packet capture file: $file (${size_mb}MB)" >> "$LOG_FILE"
        done
    fi

    # Monitor libpcap library usage
    if lsof 2>/dev/null | grep -q "libpcap"; then
        pcap_users=$(lsof 2>/dev/null | grep "libpcap" | awk '{print $1, $2}' | sort -u)
        echo "$pcap_users" | while read -r proc pid; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Process using libpcap: $proc (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Monitor BPF (Berkeley Packet Filter) usage
    if [[ -d /sys/fs/bpf ]]; then
        bpf_progs=$(find /sys/fs/bpf -type f 2>/dev/null | wc -l)
        if [[ $bpf_progs -gt 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] BPF programs loaded: $bpf_progs" >> "$LOG_FILE"
        fi
    fi

    # Check for network sniffing libraries
    if ps aux | grep -v grep | grep -qE "scapy|nmap.*-sn|ettercap"; then
        sniff_tools=$(ps aux | grep -v grep | grep -E "scapy|nmap.*-sn|ettercap" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Network sniffing tool: $sniff_tools" >> "$LOG_FILE"
    fi

    sleep 5
done
