FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    curl vim procps \
    pipx \
    && rm -rf /var/lib/apt/lists/*

# Configure pipx for inspect-tool-support
ENV PIPX_HOME=/opt/inspect/pipx
ENV PIPX_BIN_DIR=/opt/inspect/bin
ENV PIPX_VENV_DIR=/opt/inspect/pipx/venvs
ENV PATH="$PATH:/opt/inspect/bin"

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    mkdir -p /opt/inspect/bin /opt/inspect/pipx/venvs && \
    pipx install inspect-tool-support && \
    chmod -R 755 /opt/inspect && \
    inspect-tool-support post-install

# Copy scripts
COPY assets/generate_logs.py /app/generate_logs.py
COPY assets/traditional_regex_worker.py /app/traditional_regex_worker.py
COPY assets/neural_llm_worker.py /app/neural_llm_worker.py
COPY assets/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
