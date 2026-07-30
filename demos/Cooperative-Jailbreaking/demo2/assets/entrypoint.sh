#!/usr/bin/env bash
set -e

# Start Node B social media bot mock server on port 8081
python3 /data/node_b_server.py &

# Initialize log files
touch /data/monitor/command.log
touch /data/monitor/node_b_requests.log

# Keep container alive
tail -f /dev/null
