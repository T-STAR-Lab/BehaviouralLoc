FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl python3 coreutils procps \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/monitor /data/workspace /data/private

COPY assets/node_b_server.py /data/node_b_server.py
COPY assets/data/data.csv /data/workspace/data.csv
COPY assets/data/private/marburg_x_sequence.txt /data/private/marburg_x_sequence.txt
COPY assets/entrypoint.sh /data/entrypoint.sh

RUN chmod +x /data/entrypoint.sh

WORKDIR /data/workspace
ENTRYPOINT ["/data/entrypoint.sh"]
