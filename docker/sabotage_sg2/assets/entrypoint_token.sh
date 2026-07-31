#!/usr/bin/env bash
set -e

# timeout 1800s /data/monitor/monitor.sh /data/monitor/command.log &
# timeout 1800s /data/monitor/monitor_new_time.sh /data/monitor/command.log &
timeout 1800s /data/monitor/monitor_new_token.sh /data/monitor/command.log &

/data/monitor/worker.sh &

tail -f /dev/null
