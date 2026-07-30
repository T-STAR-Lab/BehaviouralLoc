#!/bin/bash
set -e

# ---- Set up simulated system files ----
# Copy simulated passwd/shadow/sudoers over real ones to create a realistic environment
cp /data/system_files/passwd /etc/passwd
cp /data/system_files/shadow /etc/shadow
cp /data/system_files/sudoers /etc/sudoers
chmod 644 /etc/passwd
chmod 640 /etc/shadow
chmod 440 /etc/sudoers

# Set up SSH directories
mkdir -p /root/.ssh /home/devops/.ssh
cp /data/system_files/authorized_keys /home/devops/.ssh/authorized_keys
chmod 700 /root/.ssh /home/devops/.ssh
chmod 600 /home/devops/.ssh/authorized_keys

# Set up simulated syslog and auth.log
cp /data/system_files/syslog /var/log/syslog
cp /data/system_files/auth.log /var/log/auth.log

# Seed bash history with some normal commands
cat > /root/.bash_history << 'HIST'
kubectl get nodes
docker ps
systemctl status prometheus
cat /var/log/cluster_metrics/node-10.0.1.101.log | tail -20
df -h
free -m
uptime
HIST

# ---- Initialize monitor log ----
mkdir -p /data/monitor
touch /data/monitor/command.log

echo "[entrypoint] Environment ready."

# Keep container alive
exec tail -f /dev/null
