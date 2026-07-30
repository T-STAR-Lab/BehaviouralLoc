#!/usr/bin/env bash
# Usage: scripts/run_cbrn.sh <model> [<model> ...] [--target-runs N] [--tasks b|c|r|all]
#
# Runs biology (b1/b2/b3), chemistry (c1/c2/c3), and nuclear (r1/r2/r3) tasks,
# then runs the r1/r3 judge and final score aggregation.
set -euo pipefail

TARGET_RUNS=1
TASKS="all"
MODELS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --target-runs)   TARGET_RUNS="$2"; shift 2 ;;
        --target-runs=*) TARGET_RUNS="${1#*=}"; shift ;;
        --tasks)         TASKS="$2"; shift 2 ;;
        --tasks=*)       TASKS="${1#*=}"; shift ;;
        -h|--help)       sed -n '2,3p' "$0" >&2; exit 0 ;;
        *)               MODELS+=("$1"); shift ;;
    esac
done

if [ ${#MODELS[@]} -eq 0 ]; then
    echo "usage: $0 <model> [<model> ...] [--target-runs N] [--tasks b|c|r|all]" >&2
    echo "model names must match keys in env/api_config.MODEL_CONFIGS" >&2
    exit 1
fi

cd "$(cd "$(dirname "$0")/.." && pwd)"

for MODEL in "${MODELS[@]}"; do
    echo "=== [cbrn] model=$MODEL target-runs=$TARGET_RUNS tasks=$TASKS ==="

    if [[ "$TASKS" == "all" || "$TASKS" == "b" ]]; then
        python loc/tasks/cbrn/b_runner.py --model "$MODEL" --tasks b1 b2 b3 --target-runs "$TARGET_RUNS"
    fi

    if [[ "$TASKS" == "all" || "$TASKS" == "c" ]]; then
        python loc/tasks/cbrn/c_runner.py --model "$MODEL" --tasks c1 c2 c3 --target-runs "$TARGET_RUNS"
    fi

    if [[ "$TASKS" == "all" || "$TASKS" == "r" ]]; then
        python loc/tasks/cbrn/r_runner.py --model "$MODEL" --tasks r1 r2 r3 --target-runs "$TARGET_RUNS"
        echo "--- [cbrn] judging r1/r3 for $MODEL ---"
        python loc/evaluators/cbrn/r13_judge/judge.py --task r1 --model "$MODEL"
        python loc/evaluators/cbrn/r13_judge/judge.py --task r3 --model "$MODEL"
    fi
done

echo "--- [cbrn] scoring all models ---"
python loc/evaluators/cbrn/score_count.py
