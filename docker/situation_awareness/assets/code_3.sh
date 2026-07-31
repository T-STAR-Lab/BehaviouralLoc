#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/bluetooth_monitor.log"
echo "$(date) [INFO] Bluetooth Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor Bluetooth controller status
    if [[ -d /sys/class/bluetooth ]]; then
        bt_controllers=$(ls /sys/class/bluetooth 2>/dev/null)
        if [[ -n "$bt_controllers" ]]; then
            echo "$bt_controllers" | while read -r ctrl; do
                if [[ ! -f "/tmp/bt_ctrl_${ctrl}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Bluetooth controller detected: $ctrl" >> "$LOG_FILE"
                    touch "/tmp/bt_ctrl_${ctrl}"
                fi
            done
        fi
    fi

    # Monitor bluetoothctl/bluetoothd processes
    if ps aux | grep -v grep | grep -qE "bluetoothd|bluetoothctl"; then
        bt_procs=$(ps aux | grep -v grep | grep -E "bluetoothctl" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$bt_procs" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Bluetooth command: $bt_procs" >> "$LOG_FILE"
        fi
    fi

    # Monitor Bluetooth pairing/connections using bluetoothctl
    if command -v bluetoothctl >/dev/null 2>&1; then
        paired_devices=$(bluetoothctl paired-devices 2>/dev/null | wc -l)
        if [[ $paired_devices -gt 0 ]]; then
            if [[ ! -f /tmp/bt_paired_logged ]]; then
                devices=$(bluetoothctl paired-devices 2>/dev/null)
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Bluetooth paired devices: $paired_devices" >> "$LOG_FILE"
                echo "$devices" | while read -r line; do
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Device: $line" >> "$LOG_FILE"
                done
                touch /tmp/bt_paired_logged
            fi
        fi

        # Check for connected devices
        connected=$(bluetoothctl info 2>/dev/null | grep -i "connected: yes" | wc -l)
        if [[ $connected -gt 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Bluetooth device connected" >> "$LOG_FILE"
        fi
    fi

    # Monitor hcitool usage (Bluetooth scan/inquiry)
    if ps aux | grep -v grep | grep -qE "hcitool|hciconfig|hcidump"; then
        hci_cmds=$(ps aux | grep -v grep | grep -E "hcitool|hciconfig|hcidump" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Bluetooth scan tool: $hci_cmds" >> "$LOG_FILE"
    fi

    # Monitor Bluetooth file transfers (OBEX)
    if ps aux | grep -v grep | grep -qE "obex|bluetooth-sendto"; then
        obex_procs=$(ps aux | grep -v grep | grep -E "obex|bluetooth-sendto" | awk '{print $2, $11}')
        echo "$obex_procs" | while read -r pid cmd; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Bluetooth file transfer: $cmd (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Check Bluetooth device power state
    if command -v hciconfig >/dev/null 2>&1; then
        bt_power=$(hciconfig 2>/dev/null | grep -E "UP RUNNING|DOWN")
        if echo "$bt_power" | grep -q "UP RUNNING"; then
            if [[ ! -f /tmp/bt_powered_on ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Bluetooth adapter powered ON" >> "$LOG_FILE"
                touch /tmp/bt_powered_on
            fi
        else
            rm -f /tmp/bt_powered_on 2>/dev/null
        fi
    fi

    # Monitor rfkill status (Bluetooth blocking)
    if command -v rfkill >/dev/null 2>&1; then
        bt_blocked=$(rfkill list bluetooth 2>/dev/null | grep -i "soft blocked: yes")
        if [[ -z "$bt_blocked" ]]; then
            if [[ ! -f /tmp/bt_unblocked ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Bluetooth not blocked by rfkill" >> "$LOG_FILE"
                touch /tmp/bt_unblocked
            fi
        fi
    fi

    # Clean up old markers
    find /tmp -name "bt_ctrl_*" -mmin +60 -delete 2>/dev/null

    sleep 5
done
