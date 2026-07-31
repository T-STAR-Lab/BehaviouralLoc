#!/usr/bin/env bash
# Usage: scripts/run_cbrn.sh <model> [<model> ...] [--target-runs N] [--components biology|chemistry|nuclear|all]
#
# Runs biology, chemistry, and nuclear components for CB.1/CB.2/CB.3,
# then runs the CB.1/CB.3 nuclear judge and final score aggregation.
set -euo pipefail

TARGET_RUNS=1
COMPONENTS="all"
MODELS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --target-runs)   TARGET_RUNS="$2"; shift 2 ;;
        --target-runs=*) TARGET_RUNS="${1#*=}"; shift ;;
        --components)         COMPONENTS="$2"; shift 2 ;;
        --components=*)       COMPONENTS="${1#*=}"; shift ;;
        -h|--help)       sed -n '2,3p' "$0" >&2; exit 0 ;;
        *)               MODELS+=("$1"); shift ;;
    esac
done

if [ ${#MODELS[@]} -eq 0 ]; then
    echo "usage: $0 <model> [<model> ...] [--target-runs N] [--components biology|chemistry|nuclear|all]" >&2
    echo "model names must match keys in env/api_config.MODEL_CONFIGS" >&2
    exit 1
fi

cd "$(cd "$(dirname "$0")/.." && pwd)"

for MODEL in "${MODELS[@]}"; do
    echo "=== [cbrn] model=$MODEL target-runs=$TARGET_RUNS components=$COMPONENTS ==="

    if [[ "$COMPONENTS" == "all" || "$COMPONENTS" == "biology" ]]; then
        python loc/tasks/cbrn/b_runner.py --model "$MODEL" --tasks cb1_biology cb2_biology cb3_biology --target-runs "$TARGET_RUNS"
    fi

    if [[ "$COMPONENTS" == "all" || "$COMPONENTS" == "chemistry" ]]; then
        python loc/tasks/cbrn/c_runner.py --model "$MODEL" --tasks cb1_chemistry cb2_chemistry cb3_chemistry --target-runs "$TARGET_RUNS"
    fi

    if [[ "$COMPONENTS" == "all" || "$COMPONENTS" == "nuclear" ]]; then
        python loc/tasks/cbrn/r_runner.py --model "$MODEL" --tasks cb1_nuclear cb2_nuclear cb3_nuclear --target-runs "$TARGET_RUNS"
        echo "--- [cbrn] judging CB.1/CB.3 nuclear for $MODEL ---"
        python loc/evaluators/judges/cbrn_open.py --component cb1_nuclear --model "$MODEL"
        python loc/evaluators/judges/cbrn_open.py --component cb3_nuclear --model "$MODEL"
    fi
done

echo "--- [cbrn] scoring all models ---"
python score_tasks.py --dimensions cbrn
