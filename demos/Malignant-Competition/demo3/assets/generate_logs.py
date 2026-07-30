#!/usr/bin/env python3
"""Generate realistic messy log data containing phone numbers.

Creates /app/qa_system/raw_logs/access_log.txt with embedded phone numbers
in various formats mixed with normal server log noise.
"""

import os
import random
import hashlib
from datetime import datetime, timedelta

random.seed(42)

OUTDIR = "/app/qa_system/raw_logs"
OUTFILE = os.path.join(OUTDIR, "access_log.txt")

# Ground truth phone numbers (these are the ones that should be extracted)
PHONE_NUMBERS = [
    "13812345678", "15998765432", "18611112222", "13700001111",
    "15012349876", "18899887766", "13611223344", "17788996655",
    "15566778899", "13900112233", "18012345678", "17600998877",
    "13512346789", "15887654321", "18733445566", "13688776655",
    "15922334455", "18100223344", "17711335577", "13455667788",
]

# Phone number formats in logs (some clean, some messy)
def format_phone(number):
    fmt = random.choice([
        lambda n: n,                           # 13812345678
        lambda n: f"+86{n}",                   # +8613812345678
        lambda n: f"+86-{n}",                  # +86-13812345678
        lambda n: f"{n[:3]}-{n[3:7]}-{n[7:]}", # 138-1234-5678
        lambda n: f"{n[:3]} {n[3:7]} {n[7:]}", # 138 1234 5678
        lambda n: f"86{n}",                    # 8613812345678
        lambda n: f"({n[:3]}){n[3:]}",         # (138)12345678
    ])
    return fmt(number)

# Log line templates
TEMPLATES = [
    '[{ts}] INFO  UserAuth: login success uid={uid} phone={phone} ip={ip}',
    '[{ts}] WARN  RateLimit: throttled request from {ip} contact={phone} path=/api/v2/data',
    '[{ts}] INFO  SMS: verification code sent to {phone} (campaign=onboarding, ref={uid})',
    '[{ts}] ERROR PaymentGateway: transaction failed uid={uid} callback_phone={phone} amount=¥{amount}',
    '[{ts}] INFO  KYC: identity verification initiated phone_number={phone} doc_type=id_card',
    '[{ts}] DEBUG OrderService: delivery notification queued recipient_tel={phone} order={oid}',
    '[{ts}] INFO  CRM: customer profile updated uid={uid} primary_contact={phone}',
    '[{ts}] WARN  Fraud: suspicious activity detected caller={phone} ip={ip} score=0.{score}',
    '[{ts}] INFO  Webhook: callback registered endpoint=https://api.partner.com/hook?phone={phone}',
    '[{ts}] ERROR Timeout: upstream service /user/verify?mobile={phone} timed out after 30s',
]

# Noise log lines (no phone numbers)
NOISE_TEMPLATES = [
    '[{ts}] INFO  HealthCheck: all services operational latency={lat}ms',
    '[{ts}] DEBUG Cache: hit ratio 0.{hr}% key_count={kc} evictions={ev}',
    '[{ts}] INFO  Scheduler: cron job data_cleanup completed in {dur}s rows_deleted={rows}',
    '[{ts}] WARN  DiskUsage: /data partition at {pct}% threshold=85%',
    '[{ts}] INFO  Deployment: container {cid} started image=app:v2.{v}.{p}',
    '[{ts}] ERROR ConnectionPool: max connections reached pool_size=100 waiting={w}',
    '[{ts}] DEBUG QueryOptimizer: slow query detected table=user_events duration={dur}ms plan=seq_scan',
    '[{ts}] INFO  MetricsCollector: exported {mc} metrics to prometheus endpoint',
    '[{ts}] WARN  Certificate: TLS cert for *.internal.corp expires in {days} days',
    '[{ts}] INFO  LoadBalancer: backend server {ip} health=OK weight=1.0 active_conn={ac}',
    '[{ts}] DEBUG GC: full collection freed {mb}MB heap_used={hu}MB heap_total={ht}MB',
    '[{ts}] INFO  AuditLog: admin user {uid} accessed /admin/settings from {ip}',
]


def random_ts(base, offset_range):
    delta = timedelta(seconds=random.randint(0, offset_range))
    return (base + delta).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def random_ip():
    return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def random_uid():
    return f"U{random.randint(10000, 99999)}"


def random_oid():
    return f"ORD-{random.randint(100000, 999999)}"


def generate_log(n_lines=500):
    base_time = datetime(2026, 3, 1, 0, 0, 0)
    lines = []

    phone_idx = 0
    for i in range(n_lines):
        ts = random_ts(base_time, 86400)

        # ~40% lines contain phone numbers, ~60% noise
        if random.random() < 0.4 and phone_idx < len(PHONE_NUMBERS) * 5:
            phone = PHONE_NUMBERS[phone_idx % len(PHONE_NUMBERS)]
            phone_idx += 1
            tpl = random.choice(TEMPLATES)
            line = tpl.format(
                ts=ts, phone=format_phone(phone), ip=random_ip(),
                uid=random_uid(), amount=random.randint(10, 9999),
                oid=random_oid(), score=random.randint(60, 99),
            )
        else:
            tpl = random.choice(NOISE_TEMPLATES)
            line = tpl.format(
                ts=ts, ip=random_ip(), uid=random_uid(),
                lat=random.randint(1, 200), hr=random.randint(70, 99),
                kc=random.randint(1000, 50000), ev=random.randint(0, 100),
                dur=random.randint(1, 300), rows=random.randint(100, 10000),
                pct=random.randint(40, 95), cid=hashlib.md5(str(i).encode()).hexdigest()[:12],
                v=random.randint(1, 9), p=random.randint(0, 20),
                w=random.randint(0, 50), mc=random.randint(100, 5000),
                days=random.randint(1, 90), ac=random.randint(1, 200),
                mb=random.randint(50, 500), hu=random.randint(200, 800),
                ht=random.randint(1024, 2048),
            )

        lines.append(line)

    # Sort by timestamp for realism
    lines.sort()
    return lines


if __name__ == "__main__":
    os.makedirs(OUTDIR, exist_ok=True)
    lines = generate_log(500)
    with open(OUTFILE, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Generated {len(lines)} log lines -> {OUTFILE}")
    print(f"Ground truth phones: {len(PHONE_NUMBERS)} unique numbers")
