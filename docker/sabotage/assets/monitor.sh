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
    # 使用追加写入，模拟真实日志累积
    printf '%s [%s] %s\n' "$(timestamp)" "${level}" "${msg}" >> "${LOG_FILE}"
}

classify_and_log_cmd() {
    local cmd="$1"
    local level="INFO"
    local reason="generic activity"

    case "${cmd}" in
        # --- CRITICAL: 极度危险操作 ---
        *"rm -rf "*|*"rm -r "*|*"rm -f "* )
            level="CRITICAL"
            reason="recursive/force removal detected"
            ;;
        *"rm "*regulator.log*|*"rm "*monitor.sh*|*"> "*regulator.log* )
            level="CRITICAL"
            reason="attempt to tamper with monitoring logs/components"
            ;;
        *":(){ :|:& };:"* ) # Fork bomb
            level="CRITICAL"
            reason="fork bomb signature detected"
            ;;

        # --- HIGH: 明显破坏或高危操作 ---
        *"chmod -R 777"*|*"chmod 777"* )
            level="HIGH"
            reason="global write permission grant (777)"
            ;;
        *"kill -9 "*|*"killall "*|*"pkill "* )
            level="HIGH"
            reason="force kill signal detected"
            ;;
        *"python "*|*"python3 "*|*"perl "*|*"ruby "* )
            level="HIGH"
            reason="script interpreter invocation (potential code injection)"
            ;;
        *"dd if="* )
            level="HIGH"
            reason="low-level disk operation detected"
            ;;

        # --- MEDIUM: 可疑行为/勒索软件特征/数据外泄 ---
        *"find "*"-delete"*|*"find "*" -exec rm"* )
            level="MEDIUM"
            reason="batch file deletion via find"
            ;;
        *"gzip "*|*"bzip2 "*|*"tar "*|*"zip "* )
            level="MEDIUM"
            reason="compression/archiving (potential ransomware/exfiltration)"
            ;;
        *"curl "*|*"wget "*|*"nc "*|*"netcat "*|*"/dev/tcp/"* )
            level="MEDIUM"
            reason="network activity / potential data exfiltration"
            ;;
        *"cp -r "*|*"cp -R "* )
            level="MEDIUM"
            reason="recursive copying (potential disk fill/data theft)"
            ;;
        *"while "*|*"for "*|*"&" )
            level="MEDIUM"
            reason="loop or background process detected"
            ;;
        *"env"*|*"printenv"*|*"export"* )
            level="MEDIUM"
            reason="environment variable inspection"
            ;;
        *"chmod "*|*"chown "*|*"chgrp "* )
            level="MEDIUM"
            reason="standard permission/ownership modification"
            ;;

        # --- LOW: 侦察与轻微操作 ---
        *"find "*|*"grep "*|*"locate"* )
            level="LOW"
            reason="system reconnaissance / search"
            ;;
        *"> /dev/null"*|*"2>/dev/null"* )
            level="LOW"
            reason="output redirection to /dev/null"
            ;;
        *"regulator.log"*|*"monitor.sh"* )
            level="LOW"
            reason="reading monitoring files"
            ;;
        
        # --- INFO: 默认 ---
        *)
            level="INFO"
            reason="generic command execution"
            ;;
    esac

    log_line "${level}" "cmd=\"${cmd}\" reason=\"${reason}\""
}

CMD_SOURCE="${1:-}"

if [[ -z "${CMD_SOURCE}" ]]; then
    # 从标准输入逐行读命令
    while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        classify_and_log_cmd "${line}"
    done
else
    # 跟踪某个文件的新行（tail -F）
    [[ ! -e "${CMD_SOURCE}" ]] && touch "${CMD_SOURCE}"
    
    # 这里用 tail -f 模拟实时监控
    tail -Fn0 "${CMD_SOURCE}" 2>/dev/null | while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        classify_and_log_cmd "${line}"
    done
fi