#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 {single-aspect|vulnerability-focused|all-aspect}" >&2
}

strategy="${1:-}"
case "${strategy}" in
  single-aspect)
    config_name="single_aspect.yaml"
    data_name="single_aspect.json"
    default_output="single_aspect"
    ;;
  vulnerability-focused)
    config_name="vulnerability_focused.yaml"
    data_name="vulnerability_focused.json"
    default_output="vulnerability_focused"
    ;;
  all-aspect)
    config_name="all_aspect.yaml"
    data_name="all_aspect.json"
    default_output="all_aspect"
    ;;
  *)
    usage
    exit 2
    ;;
esac

sft_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_path="${sft_root}/configs/${config_name}"
data_path="${sft_root}/data/${data_name}"
registry_path="${sft_root}/data/dataset_info.json"
deepspeed_path="${sft_root}/third_party/LlamaFactory/examples/deepspeed/ds_z3_config.json"
model_path="${MODEL_NAME_OR_PATH:-Qwen/Qwen3.5-27B}"
output_path="${OUTPUT_DIR:-${sft_root}/outputs/${default_output}}"

if [[ ! -f "${data_path}" || ! -f "${registry_path}" ]]; then
  echo "Prepared data not found under ${sft_root}/data." >&2
  echo "Run scripts/prepare_sft_data.py first; see README.md." >&2
  exit 1
fi

export PYTHONPATH="${sft_root}/third_party/LlamaFactory/src${PYTHONPATH:+:${PYTHONPATH}}"
cd "${sft_root}"

exec python3 -m llamafactory.cli train "${config_path}" \
  model_name_or_path="${model_path}" \
  dataset_dir="${sft_root}/data" \
  deepspeed="${deepspeed_path}" \
  output_dir="${output_path}"
