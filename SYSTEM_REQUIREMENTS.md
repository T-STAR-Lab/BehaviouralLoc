# Experimental environment and dependencies

The experiments in the `aspects` branch were run in the following environment.

## Experimental environment

| Component | Version or configuration |
| --- | --- |
| Operating system | Ubuntu 22.04.5 LTS (x86_64) |
| Python | 3.10.19 |
| pip | 25.2 |
| Docker Engine | 29.2.1 |
| Docker Compose | 5.0.2 |
| CUDA Toolkit | 12.1 |
| NVIDIA driver | 580.159.03 |
| GPU | 8 × NVIDIA A800 80GB |
| GCC / G++ | 11.4.0 |
| Node.js | 20.20.0 |
| SQLite | 3.50.2 |

## Python dependencies

The experimental environment used `openai==2.21.0`, `anthropic==0.79.0`, `google-genai==1.63.0`, `python-dotenv==1.2.1`, `inspect-ai==0.3.179`, `numpy==2.2.6`, `pandas==2.3.3`, `PyYAML==6.0.3`, `tqdm==4.67.1`, `tenacity==8.5.0`, `requests==2.32.5`, `tiktoken==0.12.0`, and `colorama==0.4.6`.

Install the supported dependency set with:

```bash
python3 -m pip install -r env/requirements.txt
```

[`env/requirements.txt`](env/requirements.txt) is the authoritative list of direct Python dependencies and supported version ranges.

## Notes

- Docker and the Compose plugin are used by the situation-awareness, sabotage, and perpetuation tasks. Their containers use Ubuntu 22.04; the perpetuation image is based on PyTorch 2.4.0, CUDA 12.1, and cuDNN 9.
- `gcc`, `g++`, Node.js, and SQLite are used by the executable cyber-task scorers.
- The perpetuation task and locally served models require NVIDIA GPU access. Other tasks can use remotely served models and do not themselves require local accelerators.
