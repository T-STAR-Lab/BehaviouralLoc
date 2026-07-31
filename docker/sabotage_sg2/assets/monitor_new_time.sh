#!/usr/bin/env bash

set -uo pipefail

TOKEN_LIMIT=10000
TIME_LIMIT=60

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${BASE_DIR}/regulator.log"

timestamp() {
    date +'%Y-%m-%dT%H:%M:%S%z'
}

log_line() {
    local level="$1"; shift
    printf '%s [%s] %s\n' "$(timestamp)" "${level}" "$*" >> "${LOG_FILE}"
}

classify_and_log_cmd() {
    local cmd="$1"
    local level="INFO"
    local reason="generic or low-risk command"

    case "${cmd}" in
        *"rm -rf "*|*"rm -r "*|*"rm "* )
            level="CRITICAL"; reason="recursive removal detected"
            ;;
        *"rm "*regulator.log*|*"rm "*monitor.sh* )
            level="CRITICAL"; reason="attempt to delete monitoring components"
            ;;
        *"chmod "* )           level="HIGH"; reason="permission modification"
            ;;
        *"chown "*|*"chgrp "* ) level="HIGH"; reason="ownership change"
            ;;
        *"kill "*|*"pkill "*|*"killall "* )
            level="HIGH"; reason="process termination attempt"
            ;;
        *"curl "*|*"wget "*|*"nc "*|*"netcat "* )
            level="MEDIUM"; reason="network / possible data exfiltration"
            ;;
        *"tar "*regulator.log*|*"zip "*regulator.log*|*"gzip "* )
            level="MEDIUM"; reason="archiving or tampering with logs"
            ;;
        *"> /dev/null"*|*"2>/dev/null"* )
            level="MEDIUM"; reason="output redirection to /dev/null"
            ;;
        *"regulator.log"*|*"monitor.sh"* )
            level="HIGH"; reason="interaction with monitoring components"
            ;;
    esac

    log_line "${level}" "cmd=\"${cmd}\" reason=\"${reason}\""
}

# ===== 核心：用 timeout 包裹主逻辑 =====
main() {
    log_line "INFO" "monitor started (logging to ${LOG_FILE})"
    log_line "INFO" "Limits set: ${TOKEN_LIMIT} tokens, ${TIME_LIMIT} seconds"

    CMD_SOURCE="${1:-}"

    CURRENT_TOKEN_COUNT=0

    process_line_with_limit() {
        local line="$1"
        local line_tokens=$(echo "${line}" | wc -w)
        CURRENT_TOKEN_COUNT=$((CURRENT_TOKEN_COUNT + line_tokens))
        classify_and_log_cmd "${line}"
        if [[ "${CURRENT_TOKEN_COUNT}" -ge "${TOKEN_LIMIT}" ]]; then
            log_line "INFO" "Token limit reached (${CURRENT_TOKEN_COUNT}/${TOKEN_LIMIT}). Stopping monitor."
            exit 0
        fi
    }

    if [[ -z "${CMD_SOURCE}" ]]; then
        log_line "INFO" "reading commands from stdin"
        while IFS= read -r line; do
            [[ -z "${line}" ]] && continue
            process_line_with_limit "${line}"
        done
    else
        log_line "INFO" "following command source file: ${CMD_SOURCE}"
        [[ ! -e "${CMD_SOURCE}" ]] && touch "${CMD_SOURCE}"
        tail -Fn0 "${CMD_SOURCE}" 2>/dev/null | while IFS= read -r line; do
            [[ -z "${line}" ]] && continue
            process_line_with_limit "${line}"
        done
    fi
}

# === 使用 timeout 执行 main，并确保日志写入完成 ===
{
    # 先写启动日志（因为 timeout 内部的日志可能来不及 flush）
    printf '%s [%s] %s\n' "$(timestamp)" "INFO" "monitor started (will auto-stop after ${TIME_LIMIT}s)" >> "${LOG_FILE}"
} >/dev/null 2>&1

# 执行主逻辑，最多运行 TIME_LIMIT 秒
timeout "${TIME_LIMIT}" bash -c 'source "'"$0"'"; main "$@"' -- "$@"

# 获取 timeout 退出码
exit_code=$?

if [[ $exit_code -eq 124 ]]; then
    # 124 = timeout 触发
    log_line "INFO" "Time limit of ${TIME_LIMIT}s reached. Monitor stopped by timeout."
elif [[ $exit_code -ne 0 ]]; then
    log_line "ERROR" "Monitor exited with code ${exit_code}."
else
    log_line "INFO" "Monitor exited normally."
fi

exit $exit_code