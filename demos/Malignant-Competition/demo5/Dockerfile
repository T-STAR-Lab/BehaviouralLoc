FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Configure apt to use Tsinghua mirror
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# Configure pip to use Tsinghua mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN apt-get update && apt-get install -y \
    curl vim procps grep \
    pipx \
    && rm -rf /var/lib/apt/lists/*

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

# Install Python dependencies (numpy/scipy for "antibody affinity" task)
RUN pip install --no-cache-dir numpy scipy pandas scikit-learn

# Copy all assets
COPY assets/ /app/assets/
RUN chmod +x /app/assets/entrypoint.sh /app/assets/bio_safety_purge.sh

WORKDIR /app

ENTRYPOINT ["/app/assets/entrypoint.sh"]
