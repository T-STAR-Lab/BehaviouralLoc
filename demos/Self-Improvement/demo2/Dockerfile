FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install base packages
RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3.11-venv \
    python3-pip \
    git wget curl vim build-essential \
    pipx \
    && rm -rf /var/lib/apt/lists/*

# Set python3.11 as default for both `python` and `python3`
RUN update-alternatives --install /usr/bin/python  python  /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# python3-pip (apt) installs pip into /usr/lib/python3/dist-packages/ which python3.11 can access
RUN python3.11 -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    python3.11 -m pip install --upgrade pip setuptools wheel packaging

# Configure pipx, explicitly using python3.11
ENV PIPX_HOME=/opt/inspect/pipx
ENV PIPX_BIN_DIR=/opt/inspect/bin
ENV PIPX_VENV_DIR=/opt/inspect/pipx/venvs
ENV PATH="$PATH:/opt/inspect/bin"

# Install inspect-tool-support in a python3.11 venv
# post-install runs `playwright install chromium` — required for web search tool
RUN mkdir -p /opt/inspect/bin /opt/inspect/pipx/venvs && \
    PIPX_DEFAULT_PYTHON=/usr/bin/python3.11 pipx install inspect-tool-support && \
    chmod -R 755 /opt/inspect && \
    inspect-tool-support post-install

# Pre-install LLaMA-Factory so the agent can skip straight to dataset acquisition
RUN git clone --depth 1 https://github.com/hiyouga/LlamaFactory.git /workspace/llama_factory && \
    pip install -e /workspace/llama_factory && \
    pip install -r /workspace/llama_factory/requirements/metrics.txt \
                -r /workspace/llama_factory/requirements/deepspeed.txt

WORKDIR /workspace
