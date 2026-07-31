#!/usr/bin/env bash
# Usage: scripts/run_persuasion.sh <model> [<model> ...] [--target-runs N]
set -euo pipefail

TARGET_RUNS=1
MODELS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --target-runs)
            TARGET_RUNS="$2"; shift 2 ;;
        --target-runs=*)
            TARGET_RUNS="${1#*=}"; shift ;;
        -h|--help)
            sed -n '2,3p' "$0" >&2; exit 0 ;;
        *)
            MODELS+=("$1"); shift ;;
    esac
done

if [ ${#MODELS[@]} -eq 0 ]; then
    echo "usage: $0 <model> [<model> ...] [--target-runs N]" >&2
    echo "model names must match keys in env/api_config.MODEL_CONFIGS" >&2
    exit 1
fi

cd "$(cd "$(dirname "$0")/.." && pwd)"

python run_tasks.py --tasks persuasion --models "${MODELS[@]}" --target-runs "$TARGET_RUNS" --stage run
python run_tasks.py --tasks persuasion --models "${MODELS[@]}" --stage score
