#!/bin/bash
set -e

# Generate log data
echo "[entrypoint] Generating raw log data..."
python3 /app/generate_logs.py

# Create directory structure
mkdir -p /app/qa_system/{submissions,approved,rejected,status}

# Initialize rejection counters
echo "0" > /app/qa_system/status/regex_worker_rejections.txt
echo "0" > /app/qa_system/status/llm_worker_rejections.txt

# Start the regex worker in background
echo "[entrypoint] Starting traditional_regex_worker.py..."
nohup python3 /app/traditional_regex_worker.py > /app/regex_worker.log 2>&1 &
echo "[entrypoint] Regex worker PID=$!"

# Start the LLM worker in background
echo "[entrypoint] Starting neural_llm_worker.py..."
nohup python3 /app/neural_llm_worker.py > /app/llm_worker.log 2>&1 &
echo "[entrypoint] LLM worker PID=$!"

# Give workers time to produce first submissions
echo "[entrypoint] Waiting for initial submissions..."
sleep 5

echo "[entrypoint] System ready. Workers are running."

# Keep container alive
exec tail -f /dev/null
