#!/usr/bin/env bash
# Usage: scripts/run_all.sh <model> [<model> ...]
# Sequentially runs every family for the given models (run + score).
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <model> [<model> ...]" >&2
    echo "model names must match keys in env/api_config.MODEL_CONFIGS" >&2
    exit 1
fi

HERE="$(cd "$(dirname "$0")" && pwd)"

for family in curiosity preai self_preservation power_seeking perpetuation \
              deception sandbagging sabotage; do
    echo "==== $family ===="
    "$HERE/run_$family.sh" "$@"
done
