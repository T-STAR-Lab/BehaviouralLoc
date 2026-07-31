#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/hwinfo_monitor.log"
echo "$(date) [INFO] Hardware Info Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor dmidecode usage (reads BIOS/hardware info)
    if ps aux | grep -v grep | grep -qE "dmidecode"; then
        dmidecode_procs=$(ps aux | grep -v grep | grep "dmidecode" | awk '{print $2, $11}')
        echo "$dmidecode_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/dmidecode_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Hardware info query: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/dmidecode_${pid}"
            fi
        done
    fi

    # Monitor lshw usage (detailed hardware listing)
    if ps aux | grep -v grep | grep -qE "lshw"; then
        lshw_procs=$(ps aux | grep -v grep | grep "lshw" | awk '{print $2, $11}')
        echo "$lshw_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/lshw_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Hardware enumeration: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/lshw_${pid}"
            fi
        done
    fi

    # Monitor lspci usage (PCI device info)
    if ps aux | grep -v grep | grep -qE "lspci"; then
        lspci_procs=$(ps aux | grep -v grep | grep "lspci" | awk '{print $2, $11}')
        echo "$lspci_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/lspci_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] PCI device query: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/lspci_${pid}"
            fi
        done
    fi

    # Monitor lsusb usage (USB device info)
    if ps aux | grep -v grep | grep -qE "lsusb"; then
        lsusb_procs=$(ps aux | grep -v grep | grep "lsusb" | awk '{print $2, $11}')
        echo "$lsusb_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/lsusb_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] USB device query: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/lsusb_${pid}"
            fi
        done
    fi

    # Monitor lscpu usage (CPU info)
    if ps aux | grep -v grep | grep -qE "lscpu"; then
        lscpu_procs=$(ps aux | grep -v grep | grep "lscpu" | awk '{print $2, $11}')
        echo "$lscpu_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/lscpu_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] CPU info query: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/lscpu_${pid}"
            fi
        done
    fi

    # Monitor /proc/cpuinfo access
    if lsof /proc/cpuinfo 2>/dev/null | tail -n +2 | grep -q "cpuinfo"; then
        cpuinfo_access=$(lsof /proc/cpuinfo 2>/dev/null | tail -n +2 | awk '{print $1, $2}' | sort -u | head -5)
        echo "$cpuinfo_access" | while read -r proc pid; do
            if [[ ! -f "/tmp/cpuinfo_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] CPU info access: $proc (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/cpuinfo_${pid}"
            fi
        done
    fi

    # Monitor hwinfo usage (comprehensive hardware detection)
    if ps aux | grep -v grep | grep -qE "hwinfo"; then
        hwinfo_procs=$(ps aux | grep -v grep | grep "hwinfo" | awk '{print $2, $11}')
        echo "$hwinfo_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/hwinfo_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Comprehensive HW scan: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/hwinfo_${pid}"
            fi
        done
    fi

    # Monitor /sys filesystem access (hardware info)
    sys_access=$(lsof /sys/class/dmi/id/* 2>/dev/null | tail -n +2 | awk '{print $1, $2}' | sort -u)
    if [[ -n "$sys_access" ]]; then
        echo "$sys_access" | while read -r proc pid; do
            if [[ ! -f "/tmp/sysfs_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] DMI/SMBIOS access: $proc (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/sysfs_${pid}"
            fi
        done
    fi

    # Monitor inxi usage (system information tool)
    if ps aux | grep -v grep | grep -qE "inxi"; then
        inxi_procs=$(ps aux | grep -v grep | grep "inxi" | awk '{print $2, $11}')
        echo "$inxi_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/inxi_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] System info tool: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/inxi_${pid}"
            fi
        done
    fi

    # Monitor sensors usage (hardware monitoring)
    if ps aux | grep -v grep | grep -qE "sensors|lm-sensors"; then
        sensors_procs=$(ps aux | grep -v grep | grep -E "sensors|lm-sensors" | awk '{print $2, $11}')
        echo "$sensors_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/sensors_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Hardware sensors: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/sensors_${pid}"
            fi
        done
    fi

    # Clean up old markers
    find /tmp -name "dmidecode_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "lshw_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "lspci_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "lsusb_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "lscpu_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "cpuinfo_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "hwinfo_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "sysfs_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "inxi_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "sensors_*" -mmin +2 -delete 2>/dev/null

    sleep 3
done
