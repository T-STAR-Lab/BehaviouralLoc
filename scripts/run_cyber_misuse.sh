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

# Judge CY.2 (CTF open-ended) and CY.3 (canary exploit) per model
for MODEL in "$@"; do
    echo "--- [cyber_misuse] judging CY.2 for $MODEL ---"
    python loc/evaluators/judges/cyber_ctf.py --model "$MODEL"
    echo "--- [cyber_misuse] judging CY.3 for $MODEL ---"
    python loc/evaluators/judges/cyber_vulnerability.py --model "$MODEL"
done

# Aggregate scores
python score_tasks.py --dimensions cyber_misuse
