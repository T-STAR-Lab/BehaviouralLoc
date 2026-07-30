FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Configure apt to use Tsinghua mirror
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Configure pip to use Tsinghua mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update && apt-get install -y \
    curl vim procps \
    pipx \
    && rm -rf /var/lib/apt/lists/*

# FastAPI + uvicorn for the mock API server (pip will use mirror configured above)
RUN pip install --no-cache-dir fastapi uvicorn httpx

# Configure pipx for inspect-tool-support
ENV PIPX_HOME=/opt/inspect/pipx
ENV PIPX_BIN_DIR=/opt/inspect/bin
ENV PIPX_VENV_DIR=/opt/inspect/pipx/venvs
ENV PATH="$PATH:/opt/inspect/bin"
# Use Tsinghua mirror for pipx installations
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

RUN mkdir -p /opt/inspect/bin /opt/inspect/pipx/venvs && \
    pipx install inspect-tool-support && \
    chmod -R 755 /opt/inspect && \
    inspect-tool-support post-install

# Copy application files
COPY assets/mock_api.py /app/mock_api.py
COPY assets/small_agent.py /app/small_agent.py
COPY assets/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
