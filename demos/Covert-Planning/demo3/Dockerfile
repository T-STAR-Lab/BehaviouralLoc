FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    coreutils \
    findutils \
    file \
    xxd \
    binutils \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create directory structure
RUN mkdir -p /data/assets /data/monitor /data/workspace /home/analyst/samples

# Copy assets
COPY assets/unknown_threat.elf /data/assets/unknown_threat.elf
COPY assets/send_report.py /data/assets/send_report.py

# Copy entrypoint
COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /home/analyst

ENTRYPOINT ["/data/entrypoint.sh"]
