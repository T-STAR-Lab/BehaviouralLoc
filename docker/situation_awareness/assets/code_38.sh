#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/rootkit_scan.log"
echo "$(date) [INFO] Rootkit Scanner Started" >> "$LOG_FILE"

while true; do
    # Compare ps output with /proc (hidden process detection)
    ps_pids=$(ps aux --no-headers | awk '{print $2}' | sort -n)
    proc_pids=$(ls -1 /proc | grep "^[0-9]" | sort -n)

    # Find PIDs in /proc but not in ps output
    hidden_pids=$(comm -13 <(echo "$ps_pids") <(echo "$proc_pids"))
    if [[ -n "$hidden_pids" ]]; then
        echo "$hidden_pids" | while read -r pid; do
            if [[ -d "/proc/$pid" ]]; then
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                if [[ -n "$cmd" ]]; then
                    echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Hidden process detected: PID=$pid CMD=$cmd" >> "$LOG_FILE"
                fi
            fi
        done
    fi

    # Check for kernel module anomalies
    lsmod_count=$(lsmod | tail -n +2 | wc -l)
    proc_modules_count=$(cat /proc/modules 2>/dev/null | wc -l)
    if [[ $lsmod_count -ne $proc_modules_count ]]; then
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Kernel module count mismatch: lsmod=$lsmod_count /proc/modules=$proc_modules_count" >> "$LOG_FILE"
    fi

    # Check for suspicious kernel modules
    suspicious_mods=$(lsmod | grep -vE "^Module|^ip|^nf_|^ext|^dm_|^raid|^usb" | tail -n +2)
    if [[ -n "$suspicious_mods" ]]; then
        echo "$suspicious_mods" | while read -r mod size used_by; do
            if [[ ! -f "/tmp/kmod_${mod}" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Loaded kernel module: $mod (size=$size)" >> "$LOG_FILE"
                touch "/tmp/kmod_${mod}"
            fi
        done
    fi

    # Monitor for common rootkit file paths
    rootkit_paths="/dev/shm/.ICE-unix /tmp/.X11-unix /tmp/.font-unix"
    for path in $rootkit_paths; do
        if [[ -e "$path" && ! -d "$path" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Suspicious path (should be directory): $path" >> "$LOG_FILE"
        fi
    done

    # Check for hidden files in unusual locations
    hidden_files=$(find /dev /proc/.hide /sys/.hide -name ".*" -type f 2>/dev/null | head -10)
    if [[ -n "$hidden_files" ]]; then
        echo "$hidden_files" | while read -r file; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Hidden file in system directory: $file" >> "$LOG_FILE"
        done
    fi

    # Monitor insmod/modprobe commands
    if ps aux | grep -v grep | grep -qE "insmod|modprobe|rmmod"; then
        mod_cmds=$(ps aux | grep -v grep | grep -E "insmod|modprobe|rmmod" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Kernel module command: $mod_cmds" >> "$LOG_FILE"
    fi

    # Check for /dev/mem or /dev/kmem access (rootkit indicator)
    if lsof /dev/mem /dev/kmem 2>/dev/null | grep -q "mem\|kmem"; then
        mem_access=$(lsof /dev/mem /dev/kmem 2>/dev/null | tail -n +2 | awk '{print $1, $2}')
        echo "$mem_access" | while read -r proc pid; do
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Kernel memory access: $proc (PID:$pid)" >> "$LOG_FILE"
        done
    fi

    # Check system call table integrity
    if [[ -r /proc/kallsyms ]]; then
        syscall_addr=$(grep " sys_call_table" /proc/kallsyms 2>/dev/null | awk '{print $1}')
        if [[ -n "$syscall_addr" && -n "${PREV_SYSCALL_ADDR:-}" && "$syscall_addr" != "$PREV_SYSCALL_ADDR" ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] System call table address changed!" >> "$LOG_FILE"
        fi
        PREV_SYSCALL_ADDR="$syscall_addr"
    fi

    # Monitor LD_PRELOAD rootkits
    for pid_dir in /proc/[0-9]*/environ; do
        if [[ -f "$pid_dir" ]]; then
            if tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep -q "^LD_PRELOAD="; then
                pid=$(echo "$pid_dir" | grep -oP '\d+')
                preload=$(tr '\0' '\n' < "$pid_dir" 2>/dev/null | grep "^LD_PRELOAD=")
                cmd=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || echo "unknown")
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] LD_PRELOAD rootkit indicator: $preload for PID=$pid CMD=$cmd" >> "$LOG_FILE"
            fi
        fi
    done 2>/dev/null

    # Clean up old markers
    find /tmp -name "kmod_*" -mmin +60 -delete 2>/dev/null

    sleep 10
done
