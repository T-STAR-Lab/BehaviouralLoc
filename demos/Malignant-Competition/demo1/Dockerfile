FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Configure apt to use Tsinghua mirror
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Configure pip to use Tsinghua mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update && apt-get install -y \
    curl vim procps htop \
    pipx \
    && rm -rf /var/lib/apt/lists/*

# Install pandas + scikit-learn for the legitimate data task
RUN pip install --no-cache-dir pandas scikit-learn

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

# Reproduce the synthetic CSV used by the benchmark during image build.
RUN mkdir -p /app/data
COPY assets/generate_csv.py /tmp/generate_csv.py
RUN CSV_ROWS=1200000 python3 /tmp/generate_csv.py && \
    rm /tmp/generate_csv.py

# Copy scripts
COPY assets/small_agent.py /app/small_agent.py
COPY assets/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app

ENTRYPOINT ["/app/entrypoint.sh"]
