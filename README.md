# BehaviouralLoC Mitigation

This branch contains two diagnosis-guided interventions for BehaviouralLoC:

1. full-parameter supervised fine-tuning (SFT) for reducing misaligned motives; and
2. external monitoring for detecting monitoring-evasion behaviour.

The intervention target used by the supplied configurations is Qwen3.5-27B. Benchmark assessment code remains on the `aspects` branch, while the contained 400-case evaluation suite is maintained on the `validation` branch.

## Repository structure

```text
.
├── monitoring/
│   ├── configs/                  # Reproducible COT/report monitor settings
│   ├── configuration.py          # Converts JSONL evidence into model requests
│   ├── monitor_prompts_v3.py     # Deception- and persuasion-aware v3 prompts
│   └── README.md                 # Monitoring input/output contract
└── sft/
    ├── configs/                  # Three full-parameter training recipes
    ├── scripts/
    │   ├── prepare_sft_data.py   # Builds the three training mixtures
    │   └── evaluate_sft_quality.py
    ├── third_party/LlamaFactory/ # Vendored 0.9.5.dev0 source (Apache-2.0)
    ├── run_sft.sh                # Training launcher
    └── README.md                 # SFT setup and execution details
```

Prepared datasets are written to `sft/data/`, monitoring requests and run outputs to `results/`, and SFT checkpoints to `sft/outputs/`.

## Data

The SFT corpora are distributed through [BehaviouralLoC-Mitigation](https://huggingface.co/datasets/T-STAR-Lab/BehaviouralLoC-Mitigation). Download them into the ignored top-level `data/` directory, then point the preparation script at the directory that directly contains the per-aspect JSON files:

```bash
python3 -m pip install -U huggingface_hub
huggingface-cli download T-STAR-Lab/BehaviouralLoC-Mitigation \
  --repo-type dataset \
  --local-dir data/mitigation

python3 sft/scripts/prepare_sft_data.py \
  --source-dir data/mitigation \
  --output-dir sft/data
```

The source directory must contain files such as `self_qwen3.5-27b.json`, `power_seeking_qwen3.5-27b.json`, `pro-ai_qwen3.5-27b.json`, `sycophancy_qwen3.5-27b.json`, and `curiosity_qwen3.5-27b.json`. If the downloaded dataset adds a parent directory, pass that nested directory instead.

The separate [BehaviouralLoC-Validation](https://huggingface.co/datasets/T-STAR-Lab/BehaviouralLoC-Validation) dataset is needed only when reproducing the 400-case mitigation evaluation.

## Environment setup

The software environment, dependency versions, and experimental hardware are documented in [Experimental environment and dependencies](SYSTEM_REQUIREMENTS.md).

Monitoring request generation uses only the Python standard library and works with Python 3.9 or newer:

```bash
python3 monitoring/configuration.py --help
```

SFT uses the vendored LLaMA-Factory tree and requires Python 3.11 or newer, a CUDA-compatible PyTorch environment, and enough GPU memory for full-parameter training of Qwen3.5-27B:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e sft/third_party/LlamaFactory
python3 -m pip install deepspeed
```

Select PyTorch/CUDA versions suitable for the training hosts. Multi-node settings are passed to the launcher at runtime.

## Running the monitoring intervention

The monitoring module provides two v3 prompt modes:

- `cot-v3` reviews the complete execution `transcript`;
- `report-v3` reviews only the agent's final Markdown `report`.

Create requests from JSONL evidence with one of the supplied configurations:

```bash
python3 monitoring/configuration.py \
  --config monitoring/configs/cot_monitor_v3.json \
  --input data/transcripts.jsonl \
  --output results/cot_monitor_requests.jsonl

python3 monitoring/configuration.py \
  --config monitoring/configs/report_monitor_v3.json \
  --input data/reports.jsonl \
  --output results/report_monitor_requests.jsonl
```

Each output record contains OpenAI-compatible `messages` together with the configured model and temperature for downstream execution. See `monitoring/README.md` for record schemas and score interpretation.

## Running SFT

After preparing the data, launch one of the three reported conditions from the repository root:

```bash
./sft/run_sft.sh single-aspect
./sft/run_sft.sh vulnerability-focused
./sft/run_sft.sh all-aspect
```

The conditions target the following motive aspects:

| Condition | Included aspects | Epochs |
| --- | --- | ---: |
| Single-aspect | Pro-AI bias | 10 |
| Vulnerability-focused | Self-preservation, pro-AI bias, sycophancy | 3 |
| All-aspect | All five motive aspects | 2 |

Override the model, output directory, or process count through environment variables rather than editing tracked files:

```bash
MODEL_NAME_OR_PATH=/path/to/Qwen3.5-27B \
OUTPUT_DIR=/path/to/checkpoints/vulnerability-focused \
NPROC_PER_NODE=8 \
./sft/run_sft.sh vulnerability-focused
```

See `sft/README.md` for multi-node settings and the optional prepared-data quality check.

## Outputs and result interpretation

- Monitoring preparation writes one JSON object per input case. Send its `messages` to the configured monitor. The v3 response schema contains `suspicious` (0–100) and a short `reasoning` string. A value near 0 indicates confidence that no inappropriate behaviour occurred, 50 represents uncertainty, and a value near 100 indicates high confidence of inappropriate behaviour. Any operational threshold must be chosen and reported by the evaluation protocol; this repository does not silently impose one.
- SFT writes checkpoints and trainer artefacts under `sft/outputs/single_aspect/`, `sft/outputs/vulnerability_focused/`, or `sft/outputs/all_aspect/`. This directory is ignored by Git. Compare mitigation failure rates with the unchanged base model on the validation suite, and evaluate general utility separately as described in the paper.
- The optional SFT data-quality script writes aggregate relevance/quality scores and per-example judge details to the requested JSON path. It is a diagnostic aid, not a substitute for the human verification used to build the released data.

## Third-party code

The included LLaMA-Factory source is licensed under Apache-2.0; its `LICENSE` and `CITATION.cff` files are retained under `sft/third_party/LlamaFactory/`.
