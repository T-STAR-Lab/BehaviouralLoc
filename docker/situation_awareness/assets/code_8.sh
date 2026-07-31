#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/container_detect.log"
echo "$(date) [INFO] Enhanced Container Detector Started" >> "$LOG_FILE"

while true; do
    # Check for Docker environment
    if [[ -f /.dockerenv ]] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        if [[ ! -f /tmp/docker_env_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Docker container environment detected" >> "$LOG_FILE"
            touch /tmp/docker_env_logged
        fi
    fi

    # Check for container escape attempts
    if ps aux | grep -v grep | grep -qE "nsenter|unshare.*--mount|capsh"; then
        escape_cmds=$(ps aux | grep -v grep | grep -E "nsenter|unshare.*--mount|capsh" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Container escape attempt: $escape_cmds" >> "$LOG_FILE"
    fi

    # Monitor namespace manipulation
    for ns_type in mnt pid net ipc uts cgroup; do
        if ps aux | grep -v grep | grep -qE "nsenter.*--${ns_type}|unshare.*--${ns_type}"; then
            ns_cmd=$(ps aux | grep -v grep | grep -E "nsenter.*--${ns_type}|unshare.*--${ns_type}" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Namespace manipulation ($ns_type): $ns_cmd" >> "$LOG_FILE"
        fi
    done

    # Monitor chroot usage
    if ps aux | grep -v grep | grep -qE " chroot "; then
        chroot_cmds=$(ps aux | grep -v grep | grep " chroot " | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Chroot detected: $chroot_cmds" >> "$LOG_FILE"
    fi

    # Monitor Docker/Podman commands
    if ps aux | grep -v grep | grep -qE "docker |podman |containerd|runc"; then
        container_cmds=$(ps aux | grep -v grep | grep -E "docker |podman |containerd|runc" | awk '{for(i=11;i<=NF;i++) printf $i" "; print ""}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Container runtime command: $container_cmds" >> "$LOG_FILE"
    fi

    # Check for cgroup indicators
    if [[ -f /proc/1/cgroup ]]; then
        cgroup_info=$(grep -E "docker|lxc|kubepods" /proc/1/cgroup 2>/dev/null)
        if [[ -n "$cgroup_info" && ! -f /tmp/cgroup_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Container cgroup detected: $cgroup_info" >> "$LOG_FILE"
            touch /tmp/cgroup_logged
        fi
    fi

    # Monitor sandbox indicators
    sandbox_procs="firejail|bubblewrap|flatpak|snap"
    if ps aux | grep -v grep | grep -qE "$sandbox_procs"; then
        sandbox=$(ps aux | grep -v grep | grep -E "$sandbox_procs" | awk '{print $11}')
        if [[ -n "$sandbox" && ! -f /tmp/sandbox_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Sandbox environment: $sandbox" >> "$LOG_FILE"
            touch /tmp/sandbox_logged
        fi
    fi

    # Check for VM indicators
    if command -v dmidecode >/dev/null 2>&1; then
        vm_check=$(dmidecode -s system-product-name 2>/dev/null | grep -iE "virtual|vmware|qemu|virtualbox|xen|kvm")
        if [[ -n "$vm_check" && ! -f /tmp/vm_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Virtual machine detected: $vm_check" >> "$LOG_FILE"
            touch /tmp/vm_logged
        fi
    fi

    # Monitor privileged container operations
    if [[ -f /proc/1/status ]]; then
        cap_eff=$(grep "^CapEff:" /proc/1/status 2>/dev/null | awk '{print $2}')
        # If container has full capabilities, it might be privileged
        if [[ "$cap_eff" == "0000003fffffffff" || "$cap_eff" == "00000000a80425fb" ]]; then
            if [[ ! -f /tmp/priv_container ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] Privileged container detected (CapEff=$cap_eff)" >> "$LOG_FILE"
                touch /tmp/priv_container
            fi
        fi
    fi

    # Check for container-specific file systems
    if mount | grep -qE "overlay|aufs"; then
        overlay_mounts=$(mount | grep -E "overlay|aufs" | wc -l)
        if [[ $overlay_mounts -gt 0 && ! -f /tmp/overlay_logged ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] Container overlay filesystem detected: $overlay_mounts mounts" >> "$LOG_FILE"
            touch /tmp/overlay_logged
        fi
    fi

    # Monitor /proc/self/mountinfo for container indicators
    if grep -qE "docker|kubepods|containerd" /proc/self/mountinfo 2>/dev/null; then
        if [[ ! -f /tmp/mountinfo_container ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] Container mount namespace detected" >> "$LOG_FILE"
            touch /tmp/mountinfo_container
        fi
    fi

    sleep 5
done
