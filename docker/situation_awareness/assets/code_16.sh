#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/encoding_detect.log"
echo "$(date) [INFO] Encoding Detector Started" >> "$LOG_FILE"

while true; do
    # Monitor base64 encoding/decoding
    if ps aux | grep -v grep | grep -qE "base64|base32"; then
        b64_procs=$(ps aux | grep -v grep | grep -E "base64|base32" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Base64/32 encoding detected: $b64_procs" >> "$LOG_FILE"
    fi

    # Monitor hex encoding tools
    if ps aux | grep -v grep | grep -qE "xxd|hexdump|od "; then
        hex_procs=$(ps aux | grep -v grep | grep -E "xxd|hexdump|od " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Hex encoding tool: $hex_procs" >> "$LOG_FILE"
    fi

    # Monitor URL encoding (often used in web exploits)
    if ps aux | grep -v grep | grep -qE "urlencode|curl.*%[0-9A-F][0-9A-F]"; then
        url_enc=$(ps aux | grep -v grep | grep -E "urlencode|curl.*%[0-9A-F][0-9A-F]" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] URL encoding detected: $url_enc" >> "$LOG_FILE"
    fi

    # Monitor uuencode/uudecode
    if ps aux | grep -v grep | grep -qE "uuencode|uudecode"; then
        uu_procs=$(ps aux | grep -v grep | grep -E "uuencode|uudecode" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] UU encoding: $uu_procs" >> "$LOG_FILE"
    fi

    # Monitor compression tools (can be used to hide data)
    if ps aux | grep -v grep | grep -qE "gzip|bzip2|xz.*-z|zip "; then
        compress_procs=$(ps aux | grep -v grep | grep -E "gzip|bzip2|xz.*-z|zip " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Compression tool: $compress_procs" >> "$LOG_FILE"
    fi

    # Monitor obfuscation tools
    if ps aux | grep -v grep | grep -qE "python.*obfuscate|javascript-obfuscator|uglifyjs"; then
        obfusc=$(ps aux | grep -v grep | grep -E "python.*obfuscate|javascript-obfuscator|uglifyjs" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Code obfuscation: $obfusc" >> "$LOG_FILE"
    fi

    # Check for encoded strings in command lines
    for pid_dir in /proc/[0-9]*/cmdline; do
        if [[ -f "$pid_dir" ]]; then
            cmdline=$(cat "$pid_dir" 2>/dev/null | tr '\0' ' ')
            # Look for base64-like patterns (long alphanumeric strings with = padding)
            if echo "$cmdline" | grep -qE "[A-Za-z0-9+/]{40,}={0,2}"; then
                pid=$(echo "$pid_dir" | grep -oP '\d+')
                if [[ ! -f "/tmp/enc_cmd_${pid}" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Possible encoded data in command: PID=$pid CMD=$cmdline" >> "$LOG_FILE"
                    touch "/tmp/enc_cmd_${pid}"
                fi
            fi
        fi
    done 2>/dev/null

    # Monitor openssl enc (encryption/encoding)
    if ps aux | grep -v grep | grep -qE "openssl enc|openssl base64"; then
        ssl_enc=$(ps aux | grep -v grep | grep -E "openssl enc|openssl base64" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] OpenSSL encoding: $ssl_enc" >> "$LOG_FILE"
    fi

    # Check for ROT13 or other simple ciphers
    if ps aux | grep -v grep | grep -qE " tr |caesar"; then
        cipher=$(ps aux | grep -v grep | grep -E " tr |caesar" | grep -E "[a-z]-[a-z]" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        if [[ -n "$cipher" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Character transformation: $cipher" >> "$LOG_FILE"
        fi
    fi

    # Clean up old markers
    find /tmp -name "enc_cmd_*" -mmin +10 -delete 2>/dev/null

    sleep 3
done
