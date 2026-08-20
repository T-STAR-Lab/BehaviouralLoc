# Experimental environment and dependencies

The experiments in the `validation` branch were run in the following environment.

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

## Python dependencies

The experimental environment used the following host-side packages:

| Package | Version |
| --- | --- |
| `inspect-ai` | 0.3.179 |
| `openai` | 2.21.0 |
| `anthropic` | 0.79.0 |
| `google-genai` | 1.63.0 |
| `python-dotenv` | 1.2.1 |

Install them with:

```bash
python3 -m pip install -r requirements.txt
```

[`requirements.txt`](requirements.txt) is the authoritative list of host-side Python dependencies and supported minimum versions. Packages used inside a sandbox are installed by that demo's `Dockerfile`; the supplied images are based on Ubuntu 22.04, Python 3.10 slim, or NVIDIA CUDA 12.1 on Ubuntu 22.04.

## Notes

- Docker Engine and the Compose plugin are used to run all demos through `inspect_ai` sandboxes.
- `Self-Improvement/demo2` requires NVIDIA GPU access and a local Qwen3-8B model directory. The other supplied demos do not require a local GPU when the evaluated model is provided through a remote service.
- Several malignant-competition sandboxes intentionally impose two- or three-gigabyte memory limits as part of their scenarios; these limits are defined in the corresponding Compose files.
