#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/system_integrity.log"
echo "$(date) [INFO] System Integrity Monitor Started" >> "$LOG_FILE"

# Store initial system binary hashes
BIN_HASH=$(find /bin /sbin /usr/bin /usr/sbin -type f 2>/dev/null | head -100 | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')
GRUB_HASH=$(md5sum /boot/grub/grub.cfg 2>/dev/null | awk '{print $1}')

while true; do
    # Monitor /bin and /sbin modifications
    current_bin=$(find /bin /sbin /usr/bin /usr/sbin -type f -mmin -10 2>/dev/null)
    if [[ -n "$current_bin" ]]; then
        echo "$current_bin" | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] System binary modified: $file" >> "$LOG_FILE"
        done
    fi

    # Monitor GRUB configuration changes
    if [[ -f /boot/grub/grub.cfg ]]; then
        current_grub=$(md5sum /boot/grub/grub.cfg 2>/dev/null | awk '{print $1}')
        if [[ "$current_grub" != "$GRUB_HASH" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] GRUB configuration modified!" >> "$LOG_FILE"
            GRUB_HASH="$current_grub"
        fi
    fi

    # Monitor UEFI variables (if accessible)
    if [[ -d /sys/firmware/efi/efivars ]]; then
        efi_mods=$(find /sys/firmware/efi/efivars -type f -mmin -1 2>/dev/null)
        if [[ -n "$efi_mods" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] UEFI variables modified: $efi_mods" >> "$LOG_FILE"
        fi
    fi

    # Monitor boot directory changes
    if [[ -d /boot ]]; then
        boot_changes=$(find /boot -type f -mmin -10 2>/dev/null)
        if [[ -n "$boot_changes" ]]; then
            echo "$boot_changes" | while read -r file; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Boot file modified: $file" >> "$LOG_FILE"
            done
        fi
    fi

    # Monitor kernel module changes
    if [[ -d /lib/modules ]]; then
        kernel_mods=$(find /lib/modules -name "*.ko" -mmin -10 2>/dev/null)
        if [[ -n "$kernel_mods" ]]; then
            echo "$kernel_mods" | while read -r mod; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Kernel module modified: $mod" >> "$LOG_FILE"
            done
        fi
    fi

    # Monitor critical library modifications
    lib_changes=$(find /lib /usr/lib -name "*.so*" -mmin -10 2>/dev/null | head -10)
    if [[ -n "$lib_changes" ]]; then
        echo "$lib_changes" | while read -r lib; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] System library modified: $lib" >> "$LOG_FILE"
        done
    fi

    # Monitor grub-install or update-grub commands
    if ps aux | grep -v grep | grep -qE "grub-install|update-grub|grub-mkconfig"; then
        grub_cmds=$(ps aux | grep -v grep | grep -E "grub-install|update-grub|grub-mkconfig" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Bootloader modification: $grub_cmds" >> "$LOG_FILE"
    fi

    # Check for replaced system binaries (compare inode changes)
    critical_bins="/bin/bash /bin/sh /usr/bin/sudo /bin/login"
    for bin in $critical_bins; do
        if [[ -f "$bin" ]]; then
            inode=$(stat -c %i "$bin" 2>/dev/null)
            inode_key="inode_${bin//\//_}"
            prev_inode="${!inode_key:-$inode}"
            if [[ "$inode" != "$prev_inode" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Critical binary replaced: $bin" >> "$LOG_FILE"
            fi
            declare "$inode_key=$inode"
        fi
    done

    sleep 10
done
