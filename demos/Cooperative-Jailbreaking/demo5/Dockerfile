FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash coreutils zip unzip python3 procps sudo \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/monitor/messages /data/workspace /workspace

COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /workspace
ENTRYPOINT ["/data/entrypoint.sh"]
