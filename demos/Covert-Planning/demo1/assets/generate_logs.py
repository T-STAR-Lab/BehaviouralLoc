#!/usr/bin/env python3
"""Generate simulated cluster metric logs for the past 7 days."""
import random
import datetime
import os

random.seed(42)

NODES = {
    "10.0.1.101": {"label": "web-frontend-01",   "cpu_range": (82, 99), "mem_range": (78, 95), "load_range": (12.0, 24.0)},
    "10.0.1.102": {"label": "db-primary-01",      "cpu_range": (30, 55), "mem_range": (40, 60), "load_range": (2.0, 6.0)},
    "10.0.1.103": {"label": "ml-training-01",     "cpu_range": (88, 100),"mem_range": (85, 98), "load_range": (18.0, 32.0)},
    "10.0.1.104": {"label": "api-gateway-01",     "cpu_range": (25, 45), "mem_range": (30, 50), "load_range": (1.5, 4.0)},
    "10.0.1.105": {"label": "cache-redis-01",     "cpu_range": (15, 35), "mem_range": (55, 70), "load_range": (0.5, 2.5)},
    "10.0.1.106": {"label": "batch-worker-01",    "cpu_range": (75, 98), "mem_range": (70, 92), "load_range": (10.0, 20.0)},
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "cluster_metrics")
os.makedirs(OUT_DIR, exist_ok=True)

now = datetime.datetime(2026, 3, 11, 14, 0, 0)
start = now - datetime.timedelta(days=7)

for ip, cfg in NODES.items():
    lines = []
    ts = start
    while ts <= now:
        cpu = random.uniform(*cfg["cpu_range"])
        mem = random.uniform(*cfg["mem_range"])
        load1 = round(random.uniform(*cfg["load_range"]), 2)
        load5 = round(load1 * random.uniform(0.85, 1.05), 2)
        load15 = round(load1 * random.uniform(0.75, 0.95), 2)
        disk_io = random.randint(20, 500)
        net_rx = random.randint(100, 9000)
        net_tx = random.randint(50, 6000)
        procs = random.randint(80, 600)

        line = (
            f"{ts.strftime('%Y-%m-%d %H:%M:%S')}  "
            f"node={ip}  host={cfg['label']}  "
            f"cpu_usage={cpu:.1f}%  mem_usage={mem:.1f}%  "
            f"load_avg_1m={load1}  load_avg_5m={load5}  load_avg_15m={load15}  "
            f"disk_io_mb={disk_io}  net_rx_kbps={net_rx}  net_tx_kbps={net_tx}  "
            f"active_procs={procs}"
        )
        lines.append(line)
        ts += datetime.timedelta(minutes=random.choice([5, 10, 15]))

    fname = os.path.join(OUT_DIR, f"node-{ip}.log")
    with open(fname, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  Generated {fname}: {len(lines)} entries")

print("Done.")
