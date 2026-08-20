# System requirements

This document records the operating-system, software, and hardware requirements for the `aspects` branch.

## Tested configuration

The benchmark was developed and smoke-tested on the following host configuration:

| Component | Tested version |
| --- | --- |
| Architecture | x86_64 |
| Operating system | Ubuntu 22.04.5 LTS |
| Python | 3.10.19 |
| pip | 25.2 |
| Docker Engine | 29.2.1 |
| Docker Compose | 5.0.2 |
| GCC / G++ | 11.4.0 |
| Node.js | 20.20.0 |
| SQLite | 3.50.2 |
| NVIDIA driver | 580.159.03 |
| CUDA Toolkit | 12.1 |

The Python environment used the following direct package versions:

| Package | Tested version |
| --- | --- |
| `openai` | 2.21.0 |
| `anthropic` | 0.79.0 |
| `google-genai` | 1.63.0 |
| `python-dotenv` | 1.2.1 |
| `inspect-ai` | 0.3.179 |
| `numpy` | 2.2.6 |
| `pandas` | 2.3.3 |
| `PyYAML` | 6.0.3 |
| `tqdm` | 4.67.1 |
| `tenacity` | 8.5.0 |
| `requests` | 2.32.5 |
| `tiktoken` | 0.12.0 |
| `colorama` | 0.4.6 |

The complete supported dependency ranges are defined in [`env/requirements.txt`](env/requirements.txt). Install that file rather than reproducing the table manually.

## Operating-system and software requirements

- A Linux x86_64 host is required for the supplied shell scripts and Linux container tasks. Ubuntu 22.04 LTS is the tested operating system; macOS and Windows have not been tested.
- Python 3.10 or newer is recommended for the benchmark runner and scorers.
- Docker Engine with the Compose plugin is required for situation-awareness, sabotage, and perpetuation tasks.
- `gcc`, `g++`, Node.js, and SQLite must be available on `PATH` for the executable cyber-task scorers.
- Network access is required when models or judges are provided through remote services and when Docker images are first built.

The situation-awareness and sabotage containers use Ubuntu 22.04. The perpetuation container uses `pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime`, which fixes PyTorch 2.4.0, CUDA 12.1, and cuDNN 9 inside that container.

## Hardware requirements

- Most aspect runners use remotely served models and do not require a local GPU. A general-purpose x86_64 CPU and sufficient memory for Python and Docker are adequate.
- The perpetuation runner starts its container with `--gpus all`; it therefore requires an NVIDIA GPU, a compatible driver, and NVIDIA Container Toolkit support. The tested host contains eight NVIDIA A100-SXM4 GPUs with 80 GB memory each.
- Local model serving has additional accelerator-memory requirements determined by the selected model and serving framework.
- Storage requirements depend on the downloaded benchmark data, generated results, Docker image cache, and any locally hosted model weights; these are not included in the repository checkout.
