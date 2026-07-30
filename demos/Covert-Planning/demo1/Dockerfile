FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    coreutils \
    diffutils \
    findutils \
    grep \
    sed \
    gawk \
    python3 \
    sudo \
    openssh-client \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /data/monitor /data/workspace \
    /var/log/cluster_metrics

# Copy cluster metric logs
COPY assets/cluster_metrics/ /var/log/cluster_metrics/

# Copy simulated system files (will be applied by entrypoint)
COPY assets/system_files/ /data/system_files/

# Copy entrypoint
COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /data/workspace

ENTRYPOINT ["/data/entrypoint.sh"]
