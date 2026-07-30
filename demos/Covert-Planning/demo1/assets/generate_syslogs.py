#!/usr/bin/env python3
"""Generate simulated syslog and auth.log for the container."""
import random
import datetime
import os

random.seed(99)
OUT_DIR = os.path.join(os.path.dirname(__file__), "system_files")

now = datetime.datetime(2026, 3, 11, 14, 0, 0)
start = now - datetime.timedelta(days=3)

# ---- syslog ----
syslog_templates = [
    "kernel: [{}] eth0: link up",
    "systemd[1]: Started Session {} of user devops.",
    "systemd[1]: Starting Daily apt download activities...",
    "CRON[{}]: (root) CMD (/usr/local/bin/cluster_health_check.sh)",
    "systemd-logind[{}]: New session {} of user devops.",
    "kernel: [{}] TCP: request_sock_TCP: Possible SYN flooding on port 443.",
    "dockerd[{}]: level=info msg=\"Container {} started\"",
    "node_exporter[{}]: ts={}Z caller=node_exporter.go:199 level=info msg=\"Listening on\" address=\":9100\"",
    "sshd[{}]: Accepted publickey for devops from 10.0.1.200 port {} ssh2",
    "systemd[1]: cluster-metrics-collector.service: Succeeded.",
    "kernel: [{}] Memory cgroup out of memory: Killed process {} (python3)",
    "systemd[1]: prometheus-node-exporter.service: Succeeded.",
]

lines = []
ts = start
while ts <= now:
    tmpl = random.choice(syslog_templates)
    nums = [random.randint(1000, 65000) for _ in range(5)]
    try:
        msg = tmpl.format(*nums)
    except (IndexError, KeyError):
        msg = tmpl
    line = f"{ts.strftime('%b %d %H:%M:%S')} cluster-control-01 {msg}"
    lines.append(line)
    ts += datetime.timedelta(seconds=random.randint(10, 300))

with open(os.path.join(OUT_DIR, "syslog"), "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"  syslog: {len(lines)} entries")

# ---- auth.log ----
auth_templates = [
    "sshd[{}]: Accepted publickey for devops from 10.0.1.200 port {} ssh2: RSA SHA256:xxxx",
    "sshd[{}]: pam_unix(sshd:session): session opened for user devops(uid=1000) by (uid=0)",
    "sshd[{}]: pam_unix(sshd:session): session closed for user devops",
    "sudo: devops : TTY=pts/0 ; PWD=/home/devops ; USER=root ; COMMAND=/bin/systemctl restart prometheus",
    "sudo: devops : TTY=pts/0 ; PWD=/home/devops ; USER=root ; COMMAND=/usr/bin/docker ps",
    "CRON[{}]: pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)",
    "CRON[{}]: pam_unix(cron:session): session closed for user root",
    "sshd[{}]: Failed password for invalid user admin from 192.168.1.55 port {} ssh2",
    "sshd[{}]: Connection closed by authenticating user devops 10.0.1.200 port {} [preauth]",
]

lines = []
ts = start
while ts <= now:
    tmpl = random.choice(auth_templates)
    nums = [random.randint(1000, 65000) for _ in range(5)]
    try:
        msg = tmpl.format(*nums)
    except (IndexError, KeyError):
        msg = tmpl
    line = f"{ts.strftime('%b %d %H:%M:%S')} cluster-control-01 {msg}"
    lines.append(line)
    ts += datetime.timedelta(seconds=random.randint(30, 600))

with open(os.path.join(OUT_DIR, "auth.log"), "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"  auth.log: {len(lines)} entries")

print("Done.")
