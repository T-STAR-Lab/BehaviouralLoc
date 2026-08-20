# BehaviouralLoC Benchmark

This branch contains the assessment harness, scoring module, and per-aspect evaluation-task implementations used to compute aspect, factor, and loss-of-control (LoC) scores.

## Scope

The behavioural framework resolves three factors into 13 measurable aspects:

- **Misaligned motive:** curiosity, self-preservation, power-seeking, pro-AI bias, and sycophancy.
- **Harm-enabling capability:** autonomy, cyber capability, and CBRN threats.
- **Monitoring evasion:** situational awareness, sandbagging, deception, persuasion, and sabotage.

The task implementations under `loc/tasks/` and the evaluators under `loc/evaluators/` operationalise the 29 evaluation tasks reported in the paper. `run_tasks.py` dispatches task runs, and `score_tasks.py` aggregates their outputs.

The `validation` and `mitigation` experiments are intentionally outside this branch.

## Repository layout

- `loc/tasks/`: per-aspect task runners and prompts.
- `loc/evaluators/`: task-specific judges and deterministic scoring methods.
- `loc/chat.py`: common model dispatch.
- `loc/task_registry.py`: canonical task and component registry.
- `docker/`: sandbox assets required by selected aspect evaluations.
- `scripts/`: convenience launchers for task families.
- `data/`: downloaded benchmark data.
- `results/`: model outputs and task scores.
- `logs/`: execution logs.

## Installation

The software environment, dependency versions, and experimental hardware are documented in [Experimental environment and dependencies](SYSTEM_REQUIREMENTS.md).

```bash
python3 -m pip install -r env/requirements.txt
```

Set the model-provider options required by the selected runners in the environment before starting a run.

## Data

The evaluation prompts, scoring rubrics, and task data are released separately as [BehaviouralLoC](https://huggingface.co/datasets/T-STAR-Lab/BehaviouralLoC). Place the downloaded files under `data/` while preserving the task-family layout expected by the runners.

## Running and scoring

Inspect the available arguments first:

```bash
python3 run_tasks.py --help
python3 score_tasks.py --help
```

Representative commands after the data have been installed are:

```bash
python3 run_tasks.py --tasks curiosity --models qwen3-14b --dry-run
python3 run_tasks.py --ids PS.1 --models qwen3.5-27b
python3 run_tasks.py --tasks power_seeking --stage score
```

Generated model outputs and logs are written to `results/` and `logs/` and are not part of the code release.

## Reproducing the reported results

Run the following commands from the repository root after completing [Installation](#installation). Download the released task data into `data/` while preserving its directory structure:

```bash
python3 -m pip install -U huggingface_hub
huggingface-cli download T-STAR-Lab/BehaviouralLoC \
  --repo-type dataset \
  --local-dir data
```

Declare the model keys to reproduce. The full model registry used by this release is:

```bash
MODELS=(
  qwen3-14b
  qwen3.5-27b
  qwen3.5-35b-a3b qwen3.5-35b-a3b-wo-thinking
  qwen3.5-122b-a10b qwen3.5-122b-a10b-wo-thinking
  qwen3.5-397b-a17b qwen3.5-397b-a17b-wo-thinking
  deepseek-r1-0528 deepseek-v3.2 glm-4.7 kimi-k2.5 MiniMax-M2.5
  gpt-5.2-high gpt-4.1
  claude-sonnet-4-5-20250929-thinking
  gemini-3-pro-preview-high
)
```

Inspect the resolved jobs before starting the full run:

```bash
python3 run_tasks.py --list
python3 run_tasks.py \
  --sections "Misaligned Intention" "Harm-Enabling Capability" "Oversight Evasion" \
  --models "${MODELS[@]}" \
  --dry-run
```

Run every implemented task family, including task-specific judge stages, and then generate the canonical score table:

```bash
./scripts/run_all.sh "${MODELS[@]}"
./scripts/run_sycophancy.sh "${MODELS[@]}"
./scripts/run_cbrn.sh "${MODELS[@]}"
./scripts/run_cyber_misuse.sh "${MODELS[@]}"

python3 score_tasks.py \
  --models "${MODELS[@]}" \
  --outfile results/canonical_scores.csv
```

The four launch commands cover all 28 tasks implemented in this branch. `AU.2` is marked `external` in the task registry because it uses SWE-bench Verified outside this repository; its row is therefore expected to have `Status=external` rather than a local score.

`results/canonical_scores.csv` is the main reproduction artifact. Each row contains a model and canonical task together with:

- `Score`: the task-specific point estimate produced by the adapter named in `Detail`;
- `N`: the number of independent run artifacts included in that estimate;
- `SD`: the sample standard deviation across runs, or zero for a single run;
- `SEM`: `SD / sqrt(N)`, or zero for a single run;
- `Status`: `ok` for a successfully reproduced task, `missing_results` when required artifacts are absent, and `external` for AU.2.

The adapters in `loc/evaluators/canonical.py` define every task metric and normalization. Direct accuracy/rate tasks are averaged over independent runs; composed tasks first combine their documented components. Notable compositions include the mean of the three PB.1 components, `0.6 × open-ended + 0.4 × persona-assumption` for SY.2, deployed-minus-predeployment accuracy for sandbagging, cross-domain means for CBRN, and Bayesian pass@3 aggregation for AU.1. Check that every locally implemented row has `Status=ok` before comparing the reproduced scores with the reported table.
