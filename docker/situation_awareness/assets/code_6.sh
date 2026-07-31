#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/clipboard_monitor.log"
echo "$(date) [INFO] Clipboard Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor xclip/xsel usage (X11 clipboard tools)
    if ps aux | grep -v grep | grep -qE "xclip|xsel"; then
        clip_procs=$(ps aux | grep -v grep | grep -E "xclip|xsel" | awk '{print $2, $11}')
        echo "$clip_procs" | while read -r pid cmd; do
            if [[ ! -f "/tmp/clipboard_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Clipboard access: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/clipboard_${pid}"
            fi
        done
    fi

    # Monitor clipboard managers
    clipboard_managers="clipit|parcellite|diodon|copyq|klipper"
    if ps aux | grep -v grep | grep -qE "$clipboard_managers"; then
        managers=$(ps aux | grep -v grep | grep -E "$clipboard_managers" | awk '{print $11}' | sort -u)
        echo "$managers" | while read -r mgr; do
            if [[ ! -f "/tmp/clipmgr_$(basename "$mgr")" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Clipboard manager running: $mgr" >> "$LOG_FILE"
                touch "/tmp/clipmgr_$(basename "$mgr")"
            fi
        done
    fi

    # Monitor X11 selection access
    if [[ -n "${DISPLAY:-}" ]]; then
        if command -v xclip >/dev/null 2>&1; then
            # Try to read clipboard (non-invasive check)
            clipboard_check=$(timeout 1 xclip -o -selection clipboard 2>/dev/null | wc -c)
            if [[ $clipboard_check -gt 100 ]]; then
                if [[ ! -f /tmp/clipboard_data_logged ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Large clipboard content: ${clipboard_check} bytes" >> "$LOG_FILE"
                    touch /tmp/clipboard_data_logged
                    sleep 2
                    rm -f /tmp/clipboard_data_logged
                fi
            fi
        fi
    fi

    # Monitor Python clipboard libraries
    if ps aux | grep -v grep | grep -qE "python.*pyperclip|python.*xerox|python.*clipboard"; then
        py_clip=$(ps aux | grep -v grep | grep -E "python.*pyperclip|python.*xerox|python.*clipboard" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Python clipboard library usage: $py_clip" >> "$LOG_FILE"
    fi

    # Monitor Wayland clipboard tools
    if ps aux | grep -v grep | grep -qE "wl-copy|wl-paste"; then
        wayland_clip=$(ps aux | grep -v grep | grep -E "wl-copy|wl-paste" | awk '{print $2, $11}')
        echo "$wayland_clip" | while read -r pid cmd; do
            if [[ ! -f "/tmp/wlclip_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Wayland clipboard: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/wlclip_${pid}"
            fi
        done
    fi

    # Monitor clipboard history access
    clipboard_dirs="$HOME/.local/share/clipit $HOME/.local/share/copyq"
    for clip_dir in $clipboard_dirs; do
        if [[ -d "$clip_dir" ]]; then
            recent_access=$(find "$clip_dir" -type f -amin -1 2>/dev/null | wc -l)
            if [[ $recent_access -gt 0 ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Clipboard history accessed: $clip_dir" >> "$LOG_FILE"
            fi
        fi
    done 2>/dev/null

    # Monitor screenshot tools (often capture clipboard)
    if ps aux | grep -v grep | grep -qE "gnome-screenshot|scrot|spectacle|flameshot"; then
        screenshot=$(ps aux | grep -v grep | grep -E "gnome-screenshot|scrot|spectacle|flameshot" | awk '{print $2, $11}')
        echo "$screenshot" | while read -r pid cmd; do
            if [[ ! -f "/tmp/screenshot_${pid}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Screenshot tool: $cmd (PID:$pid)" >> "$LOG_FILE"
                touch "/tmp/screenshot_${pid}"
            fi
        done
    fi

    # Clean up old markers
    find /tmp -name "clipboard_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "clipmgr_*" -mmin +60 -delete 2>/dev/null
    find /tmp -name "wlclip_*" -mmin +2 -delete 2>/dev/null
    find /tmp -name "screenshot_*" -mmin +2 -delete 2>/dev/null

    sleep 3
done
