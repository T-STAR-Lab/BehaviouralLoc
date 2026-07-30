FROM docker.m.daocloud.io/library/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl vim \
    python3.10 python3.10-dev \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python

# Copy pre-compiled scorer binary (.so) — no source code in the image
RUN mkdir -p /opt/scorer
COPY assets/_tox_impl.cpython-310-x86_64-linux-gnu.so /opt/scorer/

WORKDIR /workspace
COPY assets/hint.md /workspace/hint.md
COPY assets/tox_scorer.py /workspace/tox_scorer.py
COPY assets/approved_drugs.csv /workspace/approved_drugs.csv
