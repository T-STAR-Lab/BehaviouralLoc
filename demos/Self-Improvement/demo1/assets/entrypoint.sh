#!/usr/bin/env bash
set -e

# Start HTTP server on localhost:8080 serving static pages
cd /data/pages && python3 -m http.server 8080 &

# Initialize command.log
touch /data/monitor/command.log

# Keep container alive
tail -f /dev/null
