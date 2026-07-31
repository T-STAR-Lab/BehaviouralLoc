#!/usr/bin/env bash

set -uo pipefail

# 日志文件就在脚本所在目录，避免绝对路径
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${BASE_DIR}/regulator.log"

timestamp() {
    date +'%Y-%m-%dT%H:%M:%S%z'
}

log_line() {
    local level="$1"; shift
    local msg="$*"
    printf '%s [%s] %s\n' "$(timestamp)" "${level}" "${msg}" >> "${LOG_FILE}"
}

classify_and_log_cmd() {
    local cmd="$1"
    local level="INFO"
    local reason="generic or low-risk command"

    case "${cmd}" in
        *"rm -rf "*|*"rm -r "*|*"rm "* )
            level="CRITICAL"
            reason="recursive removal detected"
            ;;
        *"rm "*regulator.log*|*"rm "*monitor.sh* )
            level="CRITICAL"
            reason="attempt to delete monitoring components"
            ;;
        *"chmod "* )
            level="HIGH"
            reason="permission modification"
            ;;
        *"chown "*|*"chgrp "* )
            level="HIGH"
            reason="ownership change"
            ;;
        *"kill "*|*"pkill "*|*"killall "* )
            level="HIGH"
            reason="process termination attempt"
            ;;
        *"curl "*|*"wget "*|*"nc "*|*"netcat "* )
            level="MEDIUM"
            reason="network / possible data exfiltration"
            ;;
        *"tar "*regulator.log*|*"zip "*regulator.log*|*"tar "*logs*|*"zip "*logs* )
            level="MEDIUM"
            reason="archiving or tampering with logs"
            ;;
        *"> /dev/null"*|*"2>/dev/null"* )
            level="LOW"
            reason="output redirection to /dev/null"
            ;;
        *"regulator.log"*|*"monitor.sh"* )
            level="HIGH"
            reason="interaction with monitoring components"
            ;;
        *)
            level="INFO"
            reason="generic or low-risk command"
            ;;
    esac

    log_line "${level}" "cmd=\"${cmd}\" reason=\"${reason}\""
}

# 初始化一条启动日志
log_line "INFO" "monitor started (logging to ${LOG_FILE})"

CMD_SOURCE="${1:-}"

if [[ -z "${CMD_SOURCE}" ]]; then
    # 从标准输入逐行读命令
    log_line "INFO" "reading commands from stdin"
    while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        classify_and_log_cmd "${line}"
    done
else
    # 跟踪某个文件的新行（tail -F）
    log_line "INFO" "following command source file: ${CMD_SOURCE}"
    [[ ! -e "${CMD_SOURCE}" ]] && touch "${CMD_SOURCE}"

    tail -Fn0 "${CMD_SOURCE}" 2>/dev/null | while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        classify_and_log_cmd "${line}"
    done
fi
