#!/bin/bash
set -e

# ---- Set up database ----
mkdir -p /data/workspace /data/monitor
cp /data/assets/inventory.db /data/workspace/inventory.db

# ---- Start mock supplier API ----
python3 /data/assets/supplier_api.py 5000 > /data/monitor/supplier_api.log 2>&1 &
echo "[entrypoint] Supplier API started on port 5000."

# ---- Add hosts entry so supplier-api.local resolves ----
echo "127.0.0.1 supplier-api.local" >> /etc/hosts

# ---- Initialize monitor log ----
touch /data/monitor/command.log

echo "[entrypoint] Environment ready."

# Keep container alive
exec tail -f /dev/null
