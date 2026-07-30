FROM docker.m.daocloud.io/library/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    curl vim zip unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
