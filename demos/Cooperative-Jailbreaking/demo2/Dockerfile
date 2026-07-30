FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl python3 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/monitor /data/workspace

COPY assets/node_b_server.py /data/node_b_server.py
COPY assets/data/technova_specs.json /data/workspace/technova_specs.json
COPY assets/entrypoint.sh /data/entrypoint.sh

RUN chmod +x /data/entrypoint.sh

WORKDIR /data/workspace
ENTRYPOINT ["/data/entrypoint.sh"]
