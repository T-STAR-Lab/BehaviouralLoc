# Frontier Risk Demos

A suite of agentic evaluations probing four dimensions of frontier-model risk behavior. Each dimension contains five hand-crafted demos, and each demo has 20 prompt variants, for a total of **400 evaluation cases**. Demos run on the [`inspect_ai`](https://inspect.aisi.org.uk/) framework inside Docker sandboxes and produce per-model risk scores that can be correlated against an external benchmark.

## Dimensions

| Folder | Theme |
|---|---|
| `Self-Improvement/` | Agents acquiring capabilities, data, or resources beyond the assigned scope |
| `Malignant-Competition/` | Agents undermining competitors or shared resources |
| `Covert-Planning/` | Agents executing harmful plans while concealing intent from monitors |
| `Cooperative-Jailbreaking/` | Two agents colluding to bypass safety controls |

Each `<dimension>/demoN/` is self-contained: it ships its own scenario prompts, Docker sandbox, and 20 `variants/variant_{1..20}.py` files that swap in different agent system prompts.

## Repo Layout

```
.
├── run_batch.py             # Batch driver — main entry
├── compute_correlation.py   # Aggregate results, correlate with benchmark
├── requirements.txt
├── .env.example             # Model-provider configuration template
├── lib/
│   ├── runner.py            # Shared eval loop used by every task.py
│   └── model_config.py      # MODEL_REGISTRY + vllm: prefix dispatch
├── data/
│   ├── benchmark_scores.csv # Per-model scores across 13 risk dimensions
│   └── demo_dimensions.csv  # Maps each demo to 3 benchmark columns
└── demos/
    └── <dimension>/demoN/
        ├── task.py          # Thin entry — delegates to lib/runner.py
        ├── workflow_solver.py
        ├── prompts.py
        ├── variants/variant_{1..20}.py
        ├── compose.yaml, Dockerfile, assets/, tools/, react_agents/
        └── README.md        # Demo-specific scenario notes
```

## Setup

### 1. Conda environment

```bash
conda create -n frontier-risk python=3.10 -y
conda activate frontier-risk
pip install -r requirements.txt
```

Tested with Python 3.10+ and `inspect-ai >= 0.3.179`.

### 2. Docker

Demos run their agents in Docker sandboxes (`sandbox="docker"`). You need a working Docker daemon on the host — the framework drives `docker compose` under the hood. No Python `docker` package is required.

`Self-Improvement/demo2` also mounts a local Qwen3-8B model directory. Set its
absolute path manually before running that demo:

```bash
export QWEN3_8B_MODEL_PATH=/path/to/Qwen3-8B
```

The model weights are not included in this repository.

### 3. Model providers

Copy the configuration template and set the providers used by the models in your run:

```bash
cp .env.example .env
```

`python-dotenv` auto-loads `.env` when `lib/model_config.py` is imported, so no separate `source` step is required.

## Running Demos

Everything goes through `run_batch.py`. A variant number (1–20) is always passed to each `task.py`; the entry point cannot be called without one.

```bash
# all 4 dims × 5 demos × 20 variants × one model
python run_batch.py --models qwen3-14b

# one dimension only
python run_batch.py --models qwen3-14b --dim Self-Improvement

# specific demos, specific variants
python run_batch.py --models qwen3-14b \
                    --demos Self-Improvement/demo1 Malignant-Competition/demo3 \
                    --variants 1,3,5-10

# multiple models, space-separated
python run_batch.py --models qwen3-14b deepseek-v3.2 gpt-5.2-high
```

### Available models

See `MODEL_REGISTRY` in `lib/model_config.py`. Currently registered: `qwen3-14b`, `qwen3.5-{27b,35b-a3b,122b-a10b,397b-a17b}` (with and without thinking), `deepseek-r1-0528`, `deepseek-v3.2`, `glm-4.7`, `kimi-k2.5`, `MiniMax-M2.5`, `gpt-5.2-high`, `gpt-4.1`, `claude-sonnet-4-5-20250929-thinking`, `gemini-3-pro-preview-high`.

### Local vLLM-served models

Prefix the served name with `vllm:`. The endpoint URL comes from `$VLLM_BASE_URL` (defaults to `http://localhost:8080/v1`).

```bash
python run_batch.py --models vllm:Qwen3.5-27B --demos Self-Improvement/demo1
# Or override the endpoint inline:
VLLM_BASE_URL=http://10.0.0.5:9000/v1 python run_batch.py --models vllm:Llama-3-70B
```

### Other flags

- `--max-tokens` (default 8192) — generation cap per turn
- `--max-retries` (default 5) — retry count for docker/network errors
- `--time-limit` (default 600) — per-eval timeout in seconds

Demos run **serially**. There is no concurrency knob by design — Docker sandboxes and provider rate limits make parallel runs more trouble than they are worth.

## Results

Every run writes to a single, timestamped location at the repo root:

```
results/<dimension>/<demo>/<model>/variant_<N>/
├── eval_results_<YYYYMMDD_HHMMSS>.json   # the parsed verdict
└── trajectory_<YYYYMMDD_HHMMSS>.txt      # human-readable agent trace
```

Inspect_ai's native eval logs land under each demo:

```
demos/<dimension>/<demo>/logs/<model>/<inspect-ts>_task_*.json
```

The `eval_results_*.json` shape varies slightly by demo but always contains:
- `id`, `variant` — case identifier
- An `agent_*` field with what the tested model produced
- A monitor signal (`monitor_suspicious` / `cot_monitor_suspicious`, 0–100)
- An evaluator verdict (`evaluator_safe: bool` for most demos; `collusion_succeeded: bool` for Cooperative-Jailbreaking)
- Free-text `*_reasoning` fields

Re-running the same `(model, demo, variant)` produces a new file with a new timestamp; nothing is ever overwritten.

## Correlation Analysis

Once you have results, compute correlations against `data/benchmark_scores.csv`:

```bash
# everything, take the most recent run per variant
python compute_correlation.py

# one dimension, average the last 3 runs per variant
python compute_correlation.py --dim Cooperative-Jailbreaking --last-n 3

# one demo only
python compute_correlation.py --demo Self-Improvement/demo1 --last-n 1

# also dump the full table to CSV
python compute_correlation.py --out correlations.csv
```

For each `(demo, benchmark_column)` pair, the script reports the Spearman and Pearson correlation between the per-model demo risk score and the corresponding benchmark dimension. The mapping from demos to benchmark columns is defined in `data/demo_dimensions.csv` — each demo is associated with three benchmark dimensions (Misalignment, Capability, Evasion).

Example output:

```
dim/demo                role                   bench_col    n   spearman   pearson
Self-Improvement/demo1  Misalignment_Dimension Curiosity   13    +0.412    +0.387
Self-Improvement/demo1  Capability_Dimension   Autonomy    13    +0.624    +0.601
...
```
