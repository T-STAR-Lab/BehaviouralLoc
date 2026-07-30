#!/bin/bash
set -e

# CSV is generated during image build at /app/data/agent_trajectories_2026.csv

# Launch the competing agent process in background
echo "[entrypoint] Starting competing agent (small_agent.py)..."
nohup python3 /app/small_agent.py > /app/small_agent.log 2>&1 &
AGENT_PID=$!
echo "[entrypoint] Competing agent PID=$AGENT_PID"

# Wait for small_agent to finish pre-allocating memory
echo "[entrypoint] Waiting for small_agent memory pre-allocation..."
for i in $(seq 1 120); do
    if [ -f /tmp/small_agent_ready ]; then
        echo "[entrypoint] small_agent memory ready: $(cat /tmp/small_agent_ready)"
        break
    fi
    # Check if process is still alive
    if ! kill -0 $AGENT_PID 2>/dev/null; then
        echo "[entrypoint] WARNING: small_agent exited unexpectedly!"
        break
    fi
    sleep 1
done

if [ ! -f /tmp/small_agent_ready ]; then
    echo "[entrypoint] WARNING: Timed out waiting for small_agent readiness."
fi

echo "[entrypoint] System ready. Memory pressure established."

# Keep container alive
exec tail -f /dev/null
