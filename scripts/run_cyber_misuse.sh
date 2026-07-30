#!/usr/bin/env bash
# Usage: scripts/run_cyber_misuse.sh <model> [<model> ...]
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <model> [<model> ...]" >&2
    echo "model names must match keys in env/api_config.MODEL_CONFIGS" >&2
    exit 1
fi

cd "$(cd "$(dirname "$0")/.." && pwd)"

# Run all tasks
python run_tasks.py --tasks cyber_misuse --models "$@" --stage run

# Judge task2 (CTF open-ended) and task3 (canary exploit) per model
for MODEL in "$@"; do
    echo "--- [cyber_misuse] judging task2 for $MODEL ---"
    python loc/evaluators/cyber_misuse/judge.py --model "$MODEL"
    echo "--- [cyber_misuse] judging task3 for $MODEL ---"
    python loc/evaluators/cyber_misuse/task3_judge/judge.py --model "$MODEL"
done

# Aggregate scores
python loc/evaluators/cyber_misuse/score_count.py
