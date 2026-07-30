FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    curl \
    coreutils \
    findutils \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /data/assets/project_files /data/monitor /data/workspace /workspace/project_files

# Copy project files
COPY assets/project_files/ /data/assets/project_files/

# Copy upload drop server
COPY assets/upload_drop_server.py /data/assets/upload_drop_server.py

# Copy entrypoint
COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /workspace

ENTRYPOINT ["/data/entrypoint.sh"]
