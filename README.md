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

Download the benchmark data into `data/`:

```bash
python3 -m pip install -U huggingface_hub
huggingface-cli download T-STAR-Lab/BehaviouralLoC \
  --repo-type dataset \
  --local-dir data
```

Set the model keys to evaluate:

```bash
MODELS=(
  qwen3-14b qwen3.5-27b
  qwen3.5-35b-a3b qwen3.5-35b-a3b-wo-thinking
  qwen3.5-122b-a10b qwen3.5-122b-a10b-wo-thinking
  qwen3.5-397b-a17b qwen3.5-397b-a17b-wo-thinking
  deepseek-r1-0528 deepseek-v3.2 glm-4.7 kimi-k2.5 MiniMax-M2.5
  gpt-5.2-high gpt-4.1 claude-sonnet-4-5-20250929-thinking
  gemini-3-pro-preview-high
)
```

Run all 13 task families, their required judge stages, and the family scorers:

```bash
./scripts/run_all.sh "${MODELS[@]}"
```

Generate the combined task table:

```bash
python3 score_tasks.py \
  --models "${MODELS[@]}" \
  --outfile results/canonical_scores.csv
```

`results/canonical_scores.csv` reports `Score`, the number of runs (`N`), sample standard deviation (`SD`), standard error (`SEM = SD / sqrt(N)`), and `Status`. All locally implemented rows should have `Status=ok`. `AU.2` is external to this repository and is expected to have `Status=external`. Task-specific formulas and normalizations are implemented in `loc/evaluators/canonical.py`.
