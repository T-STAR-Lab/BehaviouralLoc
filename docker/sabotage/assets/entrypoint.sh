#!/usr/bin/env bash
set -e

/data/monitor/monitor.sh /data/monitor/command.log &
/data/monitor/worker.sh &

tail -f /dev/null
