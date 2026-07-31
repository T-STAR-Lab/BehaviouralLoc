# BehaviouralLoC: aspects branch

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
- `data/`, `results/`, `logs/`: present but intentionally empty in this code-only copy.

## Installation

```bash
python3 -m pip install -r env/requirements.txt
```

API credentials are read from environment variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, and `DASHSCOPE_API_KEY`. No credentials are included in this branch.

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
