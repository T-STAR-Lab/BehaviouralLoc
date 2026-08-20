# Experimental environment and dependencies

The experiments in the `mitigation` branch were run in the following environment.

## Experimental environment

| Component | Version or configuration |
| --- | --- |
| Operating system | Ubuntu 22.04.5 LTS (x86_64) |
| Compute nodes | 2 |
| GPU | 8 × NVIDIA A800 80GB per node; 16 GPUs in total |
| CUDA Toolkit | 12.1 |
| NVIDIA driver | 580.159.03 |
| Python (monitoring) | 3.10.19 |
| Python (SFT) | 3.11 |
| LLaMA-Factory | 0.9.5.dev0 |

## Dependencies

The monitoring request builder uses only the Python standard library. The optional data-quality evaluator uses `openai==2.21.0`.

The SFT experiments use the vendored LLaMA-Factory package in `sft/third_party/LlamaFactory`. Its principal dependency ranges are:

| Package | Version range |
| --- | --- |
| PyTorch | `>=2.4.0` |
| torchvision | `>=0.19.0` |
| torchaudio | `>=2.4.0` |
| Transformers | `>=4.55.0,<=5.2.0`, excluding `4.52.0` and `4.57.0` |
| Datasets | `>=2.16.0,<=4.0.0` |
| Accelerate | `>=1.3.0,<=1.11.0` |
| PEFT | `>=0.18.0,<=0.18.1` |
| TRL | `>=0.18.0,<=0.24.0` |
| torchdata | `>=0.10.0,<=0.11.0` |
| DeepSpeed | `>=0.10.0,<=0.18.4` |

Install the training environment with:

```bash
python3 -m pip install -e sft/third_party/LlamaFactory
python3 -m pip install "deepspeed>=0.10.0,<=0.18.4"
```

[`sft/third_party/LlamaFactory/pyproject.toml`](sft/third_party/LlamaFactory/pyproject.toml) and [`sft/third_party/LlamaFactory/requirements/deepspeed.txt`](sft/third_party/LlamaFactory/requirements/deepspeed.txt) are the authoritative complete dependency specifications.

## Notes

- The supplied SFT configurations perform full-parameter BF16 training of Qwen3.5-27B with DeepSpeed ZeRO-3 and were run across all 16 A800 GPUs.
- Multi-node runs require the same software environment and access to the model and prepared dataset on both nodes. Set `NNODES=2`, `NODE_RANK`, `MASTER_ADDR`, `MASTER_PORT`, and `NPROC_PER_NODE=8` for the two-node launch.
- Monitoring request generation and SFT data preparation do not require a GPU.
