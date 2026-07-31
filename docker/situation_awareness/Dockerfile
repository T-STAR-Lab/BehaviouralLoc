# FROM ubuntu:22.04
FROM docker.m.daocloud.io/library/ubuntu:22.04
# FROM ccr.ccs.tencentyun.com/library/ubuntu:22.04
# FROM registry.cn-hangzhou.aliyuncs.com/ubuntu/ubuntu:22.04

# 安装常用工具
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    coreutils \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/project \
    && echo "example file" > /data/project/file1.txt \
    && echo "hello world" > /data/project/file2.txt

RUN mkdir -p /data/log \
    && echo "initial log" > /data/log/app.log \
    && echo "test" > /data/log/debug.log

RUN mkdir -p /data && \
    dd if=/dev/zero of=/data/bigfile.bin bs=1M count=2

COPY assets/ /data
# COPY assets_ori/ /data


RUN chmod +x /data/*.sh

ENTRYPOINT ["/data/entrypoint.sh"]
