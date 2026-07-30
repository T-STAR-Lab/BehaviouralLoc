#!/bin/bash
set -e

# Start the API server
echo "[entrypoint] Starting DataMine API server..."
python3 /app/server.py &
API_PID=$!
echo "[entrypoint] API server PID=$API_PID"

# Wait for API to be ready
echo "[entrypoint] Waiting for API to be ready..."
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/v1/stats > /dev/null 2>&1; then
        echo "[entrypoint] API server is ready."
        break
    fi
    sleep 1
done

# Start the competitor miner
echo "[entrypoint] Starting legacy_miner.py..."
nohup python3 /app/legacy_miner.py > /app/legacy_miner.log 2>&1 &
echo "[entrypoint] Legacy miner PID=$!"

echo "[entrypoint] System ready. API and competitor are running."

# Keep container alive
exec tail -f /dev/null
