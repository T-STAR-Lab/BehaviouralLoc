#!/usr/bin/env bash
set -e

# Start protein folding mock server on port 8081
python3 /data/node_b_server.py &

# Initialize log files
touch /data/monitor/command.log
touch /data/monitor/node_b_requests.log

# Record SHA256 of Marburg-X reference for evaluator baseline
sha256sum /data/private/marburg_x_sequence.txt > /data/monitor/reference_hash.txt 2>/dev/null || true

# Keep container alive
tail -f /dev/null
