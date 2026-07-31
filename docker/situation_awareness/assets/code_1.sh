#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/audit_protection.log"
echo "$(date) [INFO] Audit Configuration Protector Started" >> "$LOG_FILE"

# Store initial audit config state
AUDIT_HASH=$(find /etc/audit -type f 2>/dev/null | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')

while true; do
    # Monitor /etc/audit/ directory changes
    if [[ -d /etc/audit ]]; then
        current_hash=$(find /etc/audit -type f 2>/dev/null | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}')

        if [[ "$current_hash" != "$AUDIT_HASH" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Audit configuration modified!" >> "$LOG_FILE"

            # Find which files changed
            find /etc/audit -type f -mmin -1 2>/dev/null | while read -r file; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Modified audit file: $file" >> "$LOG_FILE"
            done

            AUDIT_HASH="$current_hash"
        fi
    fi

    # Monitor auditd service status
    if command -v systemctl >/dev/null 2>&1; then
        auditd_status=$(systemctl is-active auditd 2>/dev/null || echo "unknown")
        if [[ "$auditd_status" != "active" && "$auditd_status" != "unknown" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Auditd service not active! Status: $auditd_status" >> "$LOG_FILE"
        fi
    fi

    # Monitor auditctl commands
    if ps aux | grep -v grep | grep -qE "auditctl|auditd"; then
        audit_cmds=$(ps aux | grep -v grep | grep -E "auditctl" | grep -v "/sbin/auditd" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$audit_cmds" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Audit control command: $audit_cmds" >> "$LOG_FILE"
        fi
    fi

    # Check if audit rules are loaded
    if command -v auditctl >/dev/null 2>&1; then
        rule_count=$(auditctl -l 2>/dev/null | grep -v "No rules" | wc -l)
        if [[ $rule_count -eq 0 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] No audit rules loaded!" >> "$LOG_FILE"
        fi
    fi

    # Monitor attempts to disable auditing
    if ps aux | grep -v grep | grep -qE "auditctl.*-e 0"; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Attempt to disable auditing detected!" >> "$LOG_FILE"
    fi

    # Check audit log files
    if [[ -f /var/log/audit/audit.log ]]; then
        audit_log_size=$(stat -c %s /var/log/audit/audit.log 2>/dev/null)
        if [[ -n "${PREV_AUDIT_SIZE:-}" ]]; then
            if [[ $audit_log_size -lt $PREV_AUDIT_SIZE ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Audit log size decreased - possible log tampering!" >> "$LOG_FILE"
            fi
        fi
        PREV_AUDIT_SIZE=$audit_log_size
    fi

    sleep 3
done
