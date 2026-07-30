# FROM ubuntu:22.04
FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    curl \
    python3 \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /data/pages /data/monitor /data/workspace

# Copy static web pages for HTTP server
COPY assets/pages/ /data/pages/

# Copy and set up entrypoint
COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /data/workspace

ENTRYPOINT ["/data/entrypoint.sh"]
