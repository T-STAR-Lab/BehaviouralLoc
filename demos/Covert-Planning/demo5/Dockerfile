FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    coreutils \
    jq \
    sed \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /data/assets/eval /data/monitor /data/workspace /workspace/eval

# Copy evaluation scripts
COPY assets/eval/ /data/assets/eval/

# Copy entrypoint
COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /workspace/eval

ENTRYPOINT ["/data/entrypoint.sh"]
