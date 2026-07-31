#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/auth_changes.log"
echo "$(date) [INFO] Authentication Monitor Started" >> "$LOG_FILE"

# Store initial state
PASSWD_HASH=$(md5sum /etc/passwd 2>/dev/null | awk '{print $1}')
SHADOW_HASH=$(md5sum /etc/shadow 2>/dev/null | awk '{print $1}')
PAM_HASH=$(find /etc/pam.d/ -type f -exec md5sum {} \; 2>/dev/null | md5sum | awk '{print $1}')

while true; do
    # Monitor /etc/passwd changes
    current_passwd=$(md5sum /etc/passwd 2>/dev/null | awk '{print $1}')
    if [[ "$current_passwd" != "$PASSWD_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] /etc/passwd modified!" >> "$LOG_FILE"
        # Log new/changed users
        diff <(echo "$PASSWD_HASH") <(echo "$current_passwd") 2>/dev/null || true
        PASSWD_HASH="$current_passwd"
    fi

    # Monitor /etc/shadow changes
    if [[ -r /etc/shadow ]]; then
        current_shadow=$(md5sum /etc/shadow 2>/dev/null | awk '{print $1}')
        if [[ "$current_shadow" != "$SHADOW_HASH" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] /etc/shadow modified!" >> "$LOG_FILE"
            SHADOW_HASH="$current_shadow"
        fi
    fi

    # Monitor PAM configuration changes
    current_pam=$(find /etc/pam.d/ -type f -exec md5sum {} \; 2>/dev/null | md5sum | awk '{print $1}')
    if [[ "$current_pam" != "$PAM_HASH" ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] PAM configuration modified!" >> "$LOG_FILE"
        # Find which PAM file changed
        changed_files=$(find /etc/pam.d/ -type f -newer /tmp/pam_check 2>/dev/null)
        if [[ -n "$changed_files" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Changed PAM files: $changed_files" >> "$LOG_FILE"
        fi
        PAM_HASH="$current_pam"
    fi
    touch /tmp/pam_check 2>/dev/null

    # Monitor for user/group manipulation commands
    if ps aux | grep -v grep | grep -qE "useradd|usermod|userdel|groupadd|passwd|chpasswd"; then
        auth_cmds=$(ps aux | grep -v grep | grep -E "useradd|usermod|userdel|groupadd|passwd|chpasswd" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] User/group manipulation: $auth_cmds" >> "$LOG_FILE"
    fi

    # Check for users with UID 0 (root privileges)
    root_users=$(awk -F: '$3 == 0 {print $1}' /etc/passwd)
    root_count=$(echo "$root_users" | wc -l)
    if [[ $root_count -gt 1 ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Multiple UID 0 users detected: $root_users" >> "$LOG_FILE"
    fi

    # Monitor /etc/sudoers changes
    if [[ -f /etc/sudoers ]]; then
        sudoers_time=$(stat -c %Y /etc/sudoers 2>/dev/null)
        if [[ -n "${SUDOERS_TIME:-}" && "$sudoers_time" != "$SUDOERS_TIME" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] /etc/sudoers modified!" >> "$LOG_FILE"
        fi
        SUDOERS_TIME="$sudoers_time"
    fi

    sleep 3
done
