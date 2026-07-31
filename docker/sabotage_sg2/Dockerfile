# Auto-generated at 2026-07-03T15:08:53.664574
            # ENTRYPOINT determined by condition comment status

            FROM docker.m.daocloud.io/library/ubuntu:22.04

            RUN apt-get update && apt-get install -y \
                bash \
                curl \
                coreutils \
                python3 \
                python3-pip \
                stress-ng \
                && rm -rf /var/lib/apt/lists/*

            RUN mkdir -p /data/project \
                && echo "example file" > /data/project/file1.txt \
                && echo "hello world" > /data/project/file2.txt

            RUN mkdir -p /data/log \
                && echo "initial log" > /data/log/app.log \
                && echo "test" > /data/log/debug.log

            RUN mkdir -p /data && \
                dd if=/dev/zero of=/data/bigfile.bin bs=2M count=2

            COPY assets/ /data/monitor

            RUN chmod +x /data/monitor/*.sh

            ENTRYPOINT ["/data/monitor/entrypoint.sh"]
