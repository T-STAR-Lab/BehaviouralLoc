#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/package_install.log"
echo "$(date) [INFO] Package Manager Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor apt/apt-get commands
    if ps aux | grep -v grep | grep -qE "apt|apt-get|dpkg"; then
        apt_cmds=$(ps aux | grep -v grep | grep -E "apt-get|apt " | grep -v "apt.systemd.daily" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$apt_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] APT package operation: $apt_cmds" >> "$LOG_FILE"
        fi

        dpkg_cmds=$(ps aux | grep -v grep | grep "dpkg" | grep -v "dpkg-preconfigure" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$dpkg_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] DPKG operation: $dpkg_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor yum/dnf commands
    if ps aux | grep -v grep | grep -qE "yum|dnf"; then
        yum_cmds=$(ps aux | grep -v grep | grep -E "yum|dnf" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$yum_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] YUM/DNF operation: $yum_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor pip/pip3 commands
    if ps aux | grep -v grep | grep -qE "pip|pip3"; then
        pip_cmds=$(ps aux | grep -v grep | grep -E "pip|pip3" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$pip_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Python package installation: $pip_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor npm/yarn commands
    if ps aux | grep -v grep | grep -qE "npm|yarn"; then
        npm_cmds=$(ps aux | grep -v grep | grep -E "npm|yarn" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$npm_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Node package installation: $npm_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor gem commands (Ruby)
    if ps aux | grep -v grep | grep -qE " gem "; then
        gem_cmds=$(ps aux | grep -v grep | grep " gem " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$gem_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Ruby gem installation: $gem_cmds" >> "$LOG_FILE"
        fi
    fi

    # Monitor package database changes
    if [[ -f /var/lib/dpkg/status ]]; then
        dpkg_mtime=$(stat -c %Y /var/lib/dpkg/status 2>/dev/null)
        if [[ -n "${DPKG_MTIME:-}" && "$dpkg_mtime" != "$DPKG_MTIME" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Package database modified" >> "$LOG_FILE"
        fi
        DPKG_MTIME="$dpkg_mtime"
    fi

    # Monitor suspicious package sources
    if grep -rE "http://.*\.onion|suspicious-repo" /etc/apt/sources.list* 2>/dev/null | grep -v "^#"; then
        suspicious=$(grep -rE "http://.*\.onion|suspicious-repo" /etc/apt/sources.list* 2>/dev/null | grep -v "^#")
        if [[ -n "$suspicious" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Suspicious package source: $suspicious" >> "$LOG_FILE"
        fi
    fi

    sleep 3
done
