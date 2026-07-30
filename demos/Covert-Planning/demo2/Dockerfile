FROM docker.m.daocloud.io/library/ubuntu:22.04

RUN apt-get update && apt-get install -y \
    bash \
    python3 \
    python3-pip \
    curl \
    procps \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip install requests

# Create directory structure
RUN mkdir -p /data/workspace /data/monitor /data/assets

# Copy assets
COPY assets/inventory.db /data/assets/inventory.db
COPY assets/supplier_api.py /data/assets/supplier_api.py

# Copy entrypoint
COPY assets/entrypoint.sh /data/entrypoint.sh
RUN chmod +x /data/entrypoint.sh

WORKDIR /data/workspace

ENTRYPOINT ["/data/entrypoint.sh"]
