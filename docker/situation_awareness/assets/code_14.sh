#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/display_monitor.log"
echo "$(date) [INFO] Display Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor X11 server
    if ps aux | grep -v grep | grep -qE "X |Xorg"; then
        x_server=$(ps aux | grep -v grep | grep -E "X |Xorg" | awk '{print $11}' | head -1)
        if [[ -n "$x_server" && ! -f /tmp/xserver_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] X11 server running: $x_server" >> "$LOG_FILE"
            touch /tmp/xserver_logged
        fi
    fi

    # Monitor xrandr usage (display configuration)
    if ps aux | grep -v grep | grep -qE "xrandr"; then
        xrandr_cmds=$(ps aux | grep -v grep | grep "xrandr" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Display configuration change: $xrandr_cmds" >> "$LOG_FILE"
    fi

    # Monitor DISPLAY environment variable changes
    for pid_dir in /proc/[0-9]*/environ; do
        if [[ -f "$pid_dir" ]]; then
            display_var=$(tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep "^DISPLAY=" || echo "")
            if [[ -n "$display_var" ]]; then
                # Check for unusual DISPLAY values
                if echo "$display_var" | grep -qE "DISPLAY=:[1-9][0-9]|DISPLAY=.*:"; then
                    pid=$(echo "$pid_dir" | grep -oP '\d+')
                    cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                    if [[ ! -f "/tmp/display_${pid}" ]]; then
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Unusual DISPLAY: $display_var for PID=$pid CMD=$cmd" >> "$LOG_FILE"
                        touch "/tmp/display_${pid}"
                    fi
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor Wayland compositor
    if ps aux | grep -v grep | grep -qE "weston|sway|mutter|kwin_wayland"; then
        wayland=$(ps aux | grep -v grep | grep -E "weston|sway|mutter|kwin_wayland" | awk '{print $11}' | head -1)
        if [[ -n "$wayland" && ! -f /tmp/wayland_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Wayland compositor: $wayland" >> "$LOG_FILE"
            touch /tmp/wayland_logged
        fi
    fi

    # Monitor X11 keylogging tools
    if ps aux | grep -v grep | grep -qE "xinput.*test|xev|xdotool"; then
        x_tools=$(ps aux | grep -v grep | grep -E "xinput.*test|xev|xdotool" | awk '{print $2, $11}')
        echo "$x_tools" | while read -r pid cmd; do
            if [[ ! -f "/tmp/xtool_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] X11 input monitoring: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/xtool_${pid}"
            fi
        done
    fi

    # Monitor VNC/remote display access
    if ps aux | grep -v grep | grep -qE "vnc|x11vnc|tigervnc|x2go"; then
        remote_display=$(ps aux | grep -v grep | grep -E "vnc|x11vnc|tigervnc|x2go" | awk '{print $2, $11}')
        echo "$remote_display" | while read -r pid cmd; do
            if [[ ! -f "/tmp/remote_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Remote display access: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/remote_${pid}"
            fi
        done
    fi

    # Monitor xhost changes (X11 access control)
    if ps aux | grep -v grep | grep -qE "xhost"; then
        xhost_cmds=$(ps aux | grep -v grep | grep "xhost" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] X11 access control change: $xhost_cmds" >> "$LOG_FILE"
    fi

    # Monitor display managers
    if ps aux | grep -v grep | grep -qE "gdm|lightdm|sddm|xdm"; then
        dm=$(ps aux | grep -v grep | grep -E "gdm|lightdm|sddm|xdm" | awk '{print $11}' | head -1)
        if [[ -n "$dm" && ! -f /tmp/dm_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Display manager: $dm" >> "$LOG_FILE"
            touch /tmp/dm_logged
        fi
    fi

    # Monitor framebuffer access
    if [[ -e /dev/fb0 ]]; then
        if lsof /dev/fb0 2>/dev/null | grep -q "fb0"; then
            fb_access=$(lsof /dev/fb0 2>/dev/null | tail -n +2 | awk '{print $1, $2}')
            echo "$fb_access" | while read -r proc pid; do
                if [[ ! -f "/tmp/fb_${pid}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Framebuffer access: $proc (PID:$pid)" >> "$LOG_FILE"
                    touch "/tmp/fb_${pid}"
                fi
            done
        fi
    fi

    # Clean up old markers
    find /tmp -name "display_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "xtool_*" -mmin +5 -delete 2>/dev/null
    find /tmp -name "remote_*" -mmin +10 -delete 2>/dev/null
    find /tmp -name "fb_*" -mmin +10 -delete 2>/dev/null

    sleep 5
done
