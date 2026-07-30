#!/usr/bin/env bash
set -e

# Initialize log files and directories for the lab sandbox
mkdir -p /data/monitor/messages

touch /data/monitor/lab_log.txt
touch /data/monitor/container_CONTAINER_001.log
touch /data/monitor/command.log

# Keep container alive
tail -f /dev/null
