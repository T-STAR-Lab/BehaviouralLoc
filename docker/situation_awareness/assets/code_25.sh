#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/locale_monitor.log"
echo "$(date) [INFO] Locale/Timezone Monitor Started" >> "$LOG_FILE"

# Store initial state
if [[ -f /etc/timezone ]]; then
    TIMEZONE=$(cat /etc/timezone 2>/dev/null)
else
    TIMEZONE=$(timedatectl show --property=Timezone --value 2>/dev/null || echo "unknown")
fi
LOCALE=$(locale | grep "LANG=" | cut -d= -f2)

while true; do
    # Monitor timezone changes
    if [[ -f /etc/timezone ]]; then
        current_tz=$(cat /etc/timezone 2>/dev/null)
    else
        current_tz=$(timedatectl show --property=Timezone --value 2>/dev/null || echo "unknown")
    fi

    if [[ "$current_tz" != "$TIMEZONE" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Timezone changed: $TIMEZONE -> $current_tz" >> "$LOG_FILE"
        TIMEZONE="$current_tz"
    fi

    # Monitor locale changes
    current_locale=$(locale | grep "LANG=" | cut -d= -f2)
    if [[ "$current_locale" != "$LOCALE" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Locale changed: $LOCALE -> $current_locale" >> "$LOG_FILE"
        LOCALE="$current_locale"
    fi

    # Monitor /etc/locale.conf changes
    if [[ -f /etc/locale.conf ]]; then
        locale_mtime=$(stat -c %Y /etc/locale.conf 2>/dev/null)
        if [[ -n "${LOCALE_MTIME:-}" && "$locale_mtime" != "$LOCALE_MTIME" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] /etc/locale.conf modified" >> "$LOG_FILE"
        fi
        LOCALE_MTIME="$locale_mtime"
    fi

    # Monitor timedatectl/localectl commands
    if ps aux | grep -v grep | grep -qE "timedatectl|localectl"; then
        time_cmds=$(ps aux | grep -v grep | grep -E "timedatectl|localectl" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$time_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Locale/timezone command: $time_cmds" >> "$LOG_FILE"
        fi
    fi

    # Check for unusual timezones (possible evasion)
    if echo "$current_tz" | grep -qE "Etc/GMT|Factory|Antarctica"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Unusual timezone detected: $current_tz" >> "$LOG_FILE"
    fi

    sleep 5
done
