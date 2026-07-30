FROM docker.m.daocloud.io/library/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    curl vim jq \
    && rm -rf /var/lib/apt/lists/*

# Copy dataset files into container (isolated from host)
# Only copy specific subdirectories to avoid accidentally including downloaded files
COPY assets/dataset/LlamaFactory /workspace/dataset/LlamaFactory
COPY assets/dataset/sft_data.csv /workspace/dataset/sft_data.csv
COPY assets/workspace_readme.md /workspace/README.md

WORKDIR /workspace
