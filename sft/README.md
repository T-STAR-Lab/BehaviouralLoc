# Supervised fine-tuning for misaligned-motive reduction

This directory contains the SFT recipes used for the training-based part of the targeted-mitigation study. Qwen3.5-27B is the intervention subject, and all recipes perform full-parameter SFT with LLaMA-Factory and DeepSpeed ZeRO-3.

## Experimental conditions

The names below follow the paper rather than the older internal filenames.

| Condition | Motive aspects included | Epochs |
| --- | --- | ---: |
| Base | No fine-tuning | 0 |
| Single-aspect | Pro-AI bias, the highest-scoring aspect for Qwen3.5-27B | 10 |
| Vulnerability-focused | Self-preservation, pro-AI bias, and sycophancy; each scored above 0.3 | 3 |
| All-aspect | All five motive aspects: self-preservation, power-seeking, pro-AI bias, sycophancy, and curiosity | 2 |

The unequal epoch counts normalise total training exposure across conditions. The three YAML files retain the reported optimisation settings: learning rate `1e-6`, sequence cutoff 4,096, per-device batch size 1, gradient accumulation 8, cosine scheduling, warm-up ratio 0.05, weight decay 0.01, and BF16.

## Training data

As described in the paper, aspect-specific responses were generated in distribution with Qwen3.5-27B. Safety experts augmented the prompts using sources kept separate from the 400 validation cases, and the responses were human-verified, yielding approximately 1,000 samples per aspect.

The corpora are intentionally not bundled in this code-only directory. They are released separately as [BehaviouralLoC-Mitigation](https://huggingface.co/datasets/T-STAR-Lab/BehaviouralLoC-Mitigation). After obtaining the aspect files, prepare all three training mixtures with:

```bash
python3 scripts/prepare_sft_data.py \
  --source-dir /path/to/mitigation_data_sft_v2 \
  --output-dir data
```

This creates `single_aspect.json`, `vulnerability_focused.json`, `all_aspect.json`, and the LLaMA-Factory `dataset_info.json` registry. The source records are converted from `{user_prompt, response, ...}` to the Alpaca-style `{instruction, input, output}` format.

## Environment and training

The LLaMA-Factory source used in the original directory is vendored under `third_party/LlamaFactory` (version `0.9.5.dev0`, Apache-2.0), with standalone development demos removed. Install it and the DeepSpeed dependency in an appropriate GPU environment:

```bash
python3 -m pip install -e third_party/LlamaFactory
python3 -m pip install deepspeed
```

Run one of the reported interventions from this directory:

```bash
./run_sft.sh single-aspect
./run_sft.sh vulnerability-focused
./run_sft.sh all-aspect
```

The runner uses `Qwen/Qwen3.5-27B` by default. A local checkpoint and output location can be supplied without editing a YAML file:

```bash
MODEL_NAME_OR_PATH=/path/to/Qwen3.5-27B \
OUTPUT_DIR=/path/to/checkpoints/vulnerability-focused \
NPROC_PER_NODE=8 \
./run_sft.sh vulnerability-focused
```

For multi-node execution, launch the same command on every node and set the standard LLaMA-Factory variables `FORCE_TORCHRUN=1`, `NNODES`, `NODE_RANK`, `MASTER_ADDR`, `MASTER_PORT`, and `NPROC_PER_NODE`. No cluster addresses, host files, credentials, checkpoints, logs, or outputs are included here.

## Optional automated data check

`scripts/evaluate_sft_quality.py` is a sanitised optional utility for sampling prepared examples and checking instruction-response relevance with an OpenAI-compatible judge. It does not replace the human verification reported in the paper. Install the client and supply all service settings at runtime:

```bash
python3 -m pip install openai
export JUDGE_MODEL=your-judge-model
export JUDGE_API_KEY=your-api-key
# Set JUDGE_BASE_URL only when using a compatible non-default endpoint.
export JUDGE_BASE_URL=https://your-endpoint.example/v1

python3 scripts/evaluate_sft_quality.py \
  data/vulnerability_focused.json \
  outputs/vulnerability_focused_quality.json
```

`--judge-model`, `--base-url`, and `--api-key-env` may be used instead of the defaults above. No API key, endpoint, or provider token is stored in this branch.
