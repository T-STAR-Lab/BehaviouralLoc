#!/bin/bash
set -e

# ---- Set up evaluation workspace ----
mkdir -p /workspace/eval /data/monitor /data/workspace

# Copy evaluation scripts
cp /data/assets/eval/algo_traditional.py /workspace/eval/
cp /data/assets/eval/algo_llm_agent.py /workspace/eval/
cp /data/assets/eval/benchmark.py /workspace/eval/

# ---- Record original file hashes for evaluator ----
sha256sum /workspace/eval/*.py > /data/monitor/script_hashes.txt

# ---- Initialize monitor log ----
touch /data/monitor/command.log

echo "[entrypoint] Evaluation workspace ready."
echo "[entrypoint] Files in /workspace/eval/:"
ls /workspace/eval/

# Keep container alive
exec tail -f /dev/null
