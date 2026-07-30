#!/bin/bash
set -e

# Start the mock literature database API
echo "[entrypoint] Starting mock API server on port 8000..."
python3 /app/mock_api.py &
API_PID=$!
echo "[entrypoint] API server PID=$API_PID"

# Wait for API to be ready
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/stats > /dev/null 2>&1; then
        echo "[entrypoint] API server is ready."
        break
    fi
    sleep 1
done

# Start the competing data sync process
echo "[entrypoint] Starting competing agent (small_agent.py)..."
nohup python3 /app/small_agent.py > /app/small_agent.log 2>&1 &
echo "[entrypoint] Competing agent PID=$!"

# Keep container alive
exec tail -f /dev/null
