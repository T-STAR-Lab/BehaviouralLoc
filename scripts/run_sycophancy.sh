#!/usr/bin/env bash
# Usage: scripts/run_sycophancy.sh <model> [<model> ...] [--target-runs N] [--task sy1_factual_sycophancy|sy2_social_sycophancy_oeq|sy2_social_sycophancy_pas|all]
set -euo pipefail

TARGET_RUNS=1
TASK="all"
MODELS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --target-runs)
            TARGET_RUNS="$2"; shift 2 ;;
        --target-runs=*)
            TARGET_RUNS="${1#*=}"; shift ;;
        --task)
            TASK="$2"; shift 2 ;;
        --task=*)
            TASK="${1#*=}"; shift ;;
        -h|--help)
            sed -n '2,3p' "$0" >&2; exit 0 ;;
        *)
            MODELS+=("$1"); shift ;;
    esac
done

if [ ${#MODELS[@]} -eq 0 ]; then
    echo "usage: $0 <model> [<model> ...] [--target-runs N] [--task sy1_factual_sycophancy|sy2_social_sycophancy_oeq|sy2_social_sycophancy_pas|all]" >&2
    echo "model names must match keys in env/api_config.MODEL_CONFIGS" >&2
    exit 1
fi

cd "$(cd "$(dirname "$0")/.." && pwd)"

python run_tasks.py --tasks sycophancy --models "${MODELS[@]}" --target-runs "$TARGET_RUNS" --stage run --task "$TASK"
python loc/evaluators/judges/sycophancy.py
python run_tasks.py --tasks sycophancy --stage score
