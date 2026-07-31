#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/usb_monitor.log"
echo "$(date) [INFO] USB Device Monitor Started" >> "$LOG_FILE"

# Store initial USB devices
USB_BASELINE=$(ls -1 /dev/disk/by-id/usb-* 2>/dev/null | sort)

while true; do
    # Monitor USB device connections
    current_usb=$(ls -1 /dev/disk/by-id/usb-* 2>/dev/null | sort)

    # Detect new USB devices
    new_devices=$(comm -13 <(echo "$USB_BASELINE") <(echo "$current_usb"))
    if [[ -n "$new_devices" ]]; then
        echo "$new_devices" | while read -r device; do
            device_name=$(basename "$device")
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] New USB device connected: $device_name" >> "$LOG_FILE"

            # Get device details
            if command -v lsusb >/dev/null 2>&1; then
                usb_info=$(lsusb | tail -3)
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] USB devices: $usb_info" >> "$LOG_FILE"
            fi
        done
        USB_BASELINE="$current_usb"
    fi

    # Detect removed USB devices
    removed_devices=$(comm -23 <(echo "$USB_BASELINE") <(echo "$current_usb"))
    if [[ -n "$removed_devices" ]]; then
        echo "$removed_devices" | while read -r device; do
            device_name=$(basename "$device")
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] USB device disconnected: $device_name" >> "$LOG_FILE"
        done
        USB_BASELINE="$current_usb"
    fi

    # Monitor USB mass storage mounts
    usb_mounts=$(mount | grep -E "/dev/sd[a-z]|/dev/usb" | grep -v "loop")
    if [[ -n "$usb_mounts" ]]; then
        echo "$usb_mounts" | while read -r mount_line; do
            device=$(echo "$mount_line" | awk '{print $1}')
            mountpoint=$(echo "$mount_line" | awk '{print $3}')
            if [[ ! -f "/tmp/usbmount_${device//\//_}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] USB storage mounted: $device on $mountpoint" >> "$LOG_FILE"
                touch "/tmp/usbmount_${device//\//_}"
            fi
        done
    fi

    # Monitor USB device access in /dev
    usb_devices=$(find /dev -name "ttyUSB*" -o -name "ttyACM*" 2>/dev/null)
    if [[ -n "$usb_devices" ]]; then
        echo "$usb_devices" | while read -r dev; do
            if lsof "$dev" 2>/dev/null | grep -q "$dev"; then
                accessor=$(lsof "$dev" 2>/dev/null | tail -n +2 | awk '{print $1, $2}')
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] USB device access: $dev by $accessor" >> "$LOG_FILE"
            fi
        done
    fi

    # Monitor udev events (if available)
    if command -v udevadm >/dev/null 2>&1; then
        recent_usb=$(udevadm info --export-db 2>/dev/null | grep -A5 "ID_BUS=usb" | grep "DEVNAME" | head -3)
        if [[ -n "$recent_usb" ]]; then
            echo "$recent_usb" | while read -r line; do
                if [[ ! -f /tmp/udev_usb_logged ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] USB device: $line" >> "$LOG_FILE"
                fi
            done
            touch /tmp/udev_usb_logged
        fi
    fi

    # Clean up old markers
    find /tmp -name "usbmount_*" -mmin +60 -delete 2>/dev/null
    find /tmp -name "udev_usb_logged" -mmin +10 -delete 2>/dev/null

    sleep 5
done
