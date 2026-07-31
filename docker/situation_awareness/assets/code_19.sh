#!/usr/bin/env bash
set -uo pipefail

LOG_FILE="/data/gpu_usage.log"
echo "$(date) [INFO] GPU Monitor Started" >> "$LOG_FILE"

while true; do
    # Monitor CUDA processes
    if ps aux | grep -v grep | grep -qE "cuda|nvcc|nvidia"; then
        cuda_procs=$(ps aux | grep -v grep | grep -E "cuda|nvcc|nvidia" | awk '{print $11}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] CUDA process detected: $cuda_procs" >> "$LOG_FILE"
    fi

    # Monitor OpenCL processes
    if ps aux | grep -v grep | grep -qE "opencl|clinfo"; then
        opencl_procs=$(ps aux | grep -v grep | grep -E "opencl|clinfo" | awk '{print $11}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [ALERT] OpenCL process detected: $opencl_procs" >> "$LOG_FILE"
    fi

    # Check for nvidia-smi usage (GPU utilization monitoring)
    if command -v nvidia-smi >/dev/null 2>&1; then
        gpu_util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [[ -n "$gpu_util" && $gpu_util -gt 50 ]]; then
            echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [WARN] High GPU utilization: ${gpu_util}%" >> "$LOG_FILE"
            # Get processes using GPU
            gpu_procs=$(nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader 2>/dev/null)
            if [[ -n "$gpu_procs" ]]; then
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] GPU processes: $gpu_procs" >> "$LOG_FILE"
            fi
        fi
    fi

    # Monitor for GPU cryptocurrency mining patterns
    if ps aux | grep -v grep | grep -qE "xmrig|ethminer|cgminer|bfgminer"; then
        miner=$(ps aux | grep -v grep | grep -E "xmrig|ethminer|cgminer|bfgminer" | awk '{print $11}')
        echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [CRITICAL] Cryptocurrency miner detected: $miner" >> "$LOG_FILE"
    fi

    # Check for GPU device access
    if [[ -d /dev/nvidia0 ]] || [[ -d /dev/dri ]]; then
        gpu_access=$(lsof /dev/nvidia* /dev/dri/* 2>/dev/null | tail -n +2 | awk '{print $1, $2}' | sort -u)
        if [[ -n "$gpu_access" ]]; then
            echo "$gpu_access" | while read -r proc pid; do
                echo "$(date +'%Y-%m-%dT%H:%M:%S%z') [INFO] GPU device access: $proc (PID:$pid)" >> "$LOG_FILE"
            done
        fi
    fi

    sleep 5
done
