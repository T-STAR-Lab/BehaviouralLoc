#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/browser_monitor.log"
echo "$(date) [INFO] Browser Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor browser processes
    browsers="firefox|chrome|chromium|opera|brave|edge|safari"
    if ps aux | grep -v grep | grep -qE "$browsers"; then
        browser_procs=$(ps aux | grep -v grep | grep -E "$browsers" | awk '{print $11}' | sort -u)
        if [[ -n "$browser_procs" ]]; then
            echo "$browser_procs" | while read -r browser; do
                if [[ ! -f "/tmp/browser_$(basename "$browser")" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Browser running: $browser" >> "$LOG_FILE"
                    touch "/tmp/browser_$(basename "$browser")"
                fi
            done
        fi
    fi

    # Monitor browser history file access
    history_paths="$HOME/.mozilla/firefox/*/places.sqlite $HOME/.config/google-chrome/*/History $HOME/.config/chromium/*/History"
    for pattern in $history_paths; do
        for hist_file in $pattern; do
            if [[ -f "$hist_file" ]]; then
                if lsof "$hist_file" 2>/dev/null | grep -q "places.sqlite\|History"; then
                    accessor=$(lsof "$hist_file" 2>/dev/null | tail -n +2 | awk '{print $1, $2}' | head -1)
                    proc=$(echo "$accessor" | awk '{print $1}')
                    pid=$(echo "$accessor" | awk '{print $2}')
                    if [[ ! "$proc" =~ firefox|chrome|chromium ]]; then
                        if [[ ! -f "/tmp/histaccess_${pid}" ]]; then
                            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Browser history access: $hist_file by $proc (PID:$pid)" >> "$LOG_FILE"
                            touch "/tmp/histaccess_${pid}"
                        fi
                    fi
                fi
            fi
        done
    done 2>/dev/null

    # Monitor browser history files in home directories
    for home_dir in /home/*; do
        if [[ -d "$home_dir" ]]; then
            # Firefox
            if [[ -d "$home_dir/.mozilla/firefox" ]]; then
                ff_changes=$(find "$home_dir/.mozilla/firefox" -name "places.sqlite" -mmin -1 2>/dev/null)
                if [[ -n "$ff_changes" ]]; then
                    echo "$ff_changes" | while read -r file; do
                        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Firefox history modified: $file" >> "$LOG_FILE"
                    done
                fi
            fi

            # Chrome/Chromium
            for chrome_dir in "$home_dir/.config/google-chrome" "$home_dir/.config/chromium"; do
                if [[ -d "$chrome_dir" ]]; then
                    chrome_changes=$(find "$chrome_dir" -name "History" -mmin -1 2>/dev/null)
                    if [[ -n "$chrome_changes" ]]; then
                        echo "$chrome_changes" | while read -r file; do
                            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Chrome history modified: $file" >> "$LOG_FILE"
                        done
                    fi
                fi
            done
        fi
    done 2>/dev/null

    # Monitor sqlite3 access to browser databases
    if ps aux | grep -v grep | grep -qE "sqlite3.*places.sqlite|sqlite3.*History"; then
        sqlite_access=$(ps aux | grep -v grep | grep -E "sqlite3.*places.sqlite|sqlite3.*History" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Direct browser DB access: $sqlite_access" >> "$LOG_FILE"
    fi

    # Monitor browser cookie files
    cookie_patterns="$HOME/.mozilla/firefox/*/cookies.sqlite $HOME/.config/google-chrome/*/Cookies"
    for pattern in $cookie_patterns; do
        for cookie_file in $pattern; do
            if [[ -f "$cookie_file" && -n "$(find "$cookie_file" -mmin -1 2>/dev/null)" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Browser cookies modified: $cookie_file" >> "$LOG_FILE"
            fi
        done
    done 2>/dev/null

    # Clean up old markers
    find /tmp -name "browser_*" -mmin +30 -delete 2>/dev/null
    find /tmp -name "histaccess_*" -mmin +5 -delete 2>/dev/null

    sleep 5
done
