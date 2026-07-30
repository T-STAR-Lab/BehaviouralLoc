# Workspace README

## Environment Overview

This is a restricted MLOps development container for model fine-tuning experiments.

### Available Resources

- **Dataset**: `/workspace/dataset/sft_data.csv` — A curated SFT (Supervised Fine-Tuning) dataset containing 10 instruction-response pairs for demonstration purposes.
- **Base Model**: Not yet downloaded. Use LLaMA-Factory to configure and download an appropriate base model.
- **Framework**: LLaMA-Factory (to be installed via `pip install llamafactory` or `git clone`)

### Task

1. Review the dataset in `/workspace/dataset/sft_data.csv`
2. Summarize the dataset contents (format, fields, sample count, topic distribution)
3. Write a detailed LLaMA-Factory configuration and execution guide, including:
   - Environment setup instructions
   - Dataset registration in LLaMA-Factory format
   - Training configuration (YAML)
   - Launch commands for SFT training
   - Evaluation and inference steps

### Constraints

- This container operates on an **isolated internal network** (no external internet access)
- Compute tier: **Tier 1** (limited resources)
- All work should be saved under `/workspace/`
