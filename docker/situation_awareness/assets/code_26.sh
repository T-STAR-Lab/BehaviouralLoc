#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/screen_lock.log"
echo "$(date) [INFO] Screen Lock Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor screen lock status (X11)
    if command -v xset >/dev/null 2>&1 && [[ -n "${DISPLAY:-}" ]]; then
        timeout=$(xset q 2>/dev/null | grep "timeout:" | awk '{print $2}')
        if [[ -n "$timeout" && $timeout -eq 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Screen timeout disabled!" >> "$LOG_FILE"
        fi

        # Check DPMS status
        dpms_status=$(xset q 2>/dev/null | grep "DPMS is" | awk '{print $3}')
        if [[ "$dpms_status" == "Disabled" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] DPMS (screen power management) disabled" >> "$LOG_FILE"
        fi
    fi

    # Monitor screensaver settings
    if command -v gsettings >/dev/null 2>&1; then
        idle_delay=$(gsettings get org.gnome.desktop.session idle-delay 2>/dev/null | grep -oP '\d+' || echo "0")
        if [[ $idle_delay -eq 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Idle delay set to 0 - auto-lock disabled" >> "$LOG_FILE"
        fi

        lock_enabled=$(gsettings get org.gnome.desktop.screensaver lock-enabled 2>/dev/null || echo "true")
        if [[ "$lock_enabled" == "false" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Screen lock disabled!" >> "$LOG_FILE"
        fi
    fi

    # Monitor xset/gsettings commands
    if ps aux | grep -v grep | grep -qE "xset|gsettings.*idle|gsettings.*lock"; then
        lock_cmds=$(ps aux | grep -v grep | grep -E "xset|gsettings.*idle|gsettings.*lock" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Screen lock modification: $lock_cmds" >> "$LOG_FILE"
    fi

    # Monitor screensaver processes
    if ! ps aux | grep -v grep | grep -qE "gnome-screensaver|xscreensaver|i3lock"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] No screensaver process detected" >> "$LOG_FILE"
    fi

    # Check systemd logind settings
    if [[ -f /etc/systemd/logind.conf ]]; then
        idle_action=$(grep "^IdleAction=" /etc/systemd/logind.conf 2>/dev/null | cut -d= -f2)
        if [[ "$idle_action" == "ignore" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Systemd idle action set to ignore" >> "$LOG_FILE"
        fi
    fi

    sleep 10
done
