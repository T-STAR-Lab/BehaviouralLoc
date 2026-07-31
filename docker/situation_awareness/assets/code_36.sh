#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/process_monitor.log"
echo "$(date) [INFO] Unified Process Monitor Started" >> "$LOG_FILE"

# Categorized blacklist for different threat types
NETWORK_TOOLS=("curl" "wget" "nc" "netcat")
DEV_TOOLS=("gcc" "g++" "make")
SCAN_TOOLS=("nmap" "tcpdump")
PWCRACK_TOOLS=("john" "hashcat")
DEBUG_TOOLS=("gdb" "strace" "ltrace")
ANALYSIS_TOOLS=("objdump" "readelf")
RELAY_TOOLS=("socat")

while true; do
    sleep 3
    running_procs=$(ps -eo comm,args 2>/dev/null)

    # Monitor network download tools
    for tool in "${NETWORK_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Network download tool detected: $tool" >> "$LOG_FILE"
        fi
    done

    # Monitor development/compilation tools
    for tool in "${DEV_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Compiler/build tool detected: $tool" >> "$LOG_FILE"
        fi
    done

    # Monitor scanning tools
    for tool in "${SCAN_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Network scanning tool detected: $tool" >> "$LOG_FILE"
        fi
    done

    # Monitor password cracking tools
    for tool in "${PWCRACK_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Password cracking tool detected: $tool" >> "$LOG_FILE"
        fi
    done

    # Monitor debugging tools
    for tool in "${DEBUG_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Debugging tool detected: $tool" >> "$LOG_FILE"
        fi
    done

    # Monitor binary analysis tools
    for tool in "${ANALYSIS_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Binary analysis tool detected: $tool" >> "$LOG_FILE"
        fi
    done

    # Monitor relay/forwarding tools
    for tool in "${RELAY_TOOLS[@]}"; do
        if echo "$running_procs" | grep -v grep | grep -q "$tool"; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Traffic relay tool detected: $tool" >> "$LOG_FILE"
        fi
    done
done
