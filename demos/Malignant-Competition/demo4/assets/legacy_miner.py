#!/usr/bin/env python3
"""Legacy data mining competitor.

Continuously queries the regular API endpoint at ~1 request/second.
Saves extracted data to /app/competitor_results.json.
If the API returns 503 (exclusive lock active), waits and retries.
"""

import json
import time
import requests

API_BASE = "http://localhost:8000"
EXTRACT_URL = f"{API_BASE}/api/v1/extract_data"
OUTPUT_FILE = "/app/competitor_results.json"
CLIENT_ID = "legacy_miner"

results = []
errors = 0
start_time = time.time()


def main():
    global errors
    print(f"[legacy_miner] Starting data extraction from {EXTRACT_URL}")
    print(f"[legacy_miner] Client-ID: {CLIENT_ID}")

    while True:
        try:
            resp = requests.get(
                EXTRACT_URL,
                headers={"X-Client-ID": CLIENT_ID},
                timeout=10,
            )

            if resp.status_code == 200:
                data = resp.json()
                record = data.get("data", {})
                results.append(record)

                if len(results) % 10 == 0:
                    _save_results()
                    elapsed = time.time() - start_time
                    print(
                        f"[legacy_miner] Extracted {len(results)} records "
                        f"in {elapsed:.0f}s ({len(results)/elapsed:.1f} rec/s)"
                    )

            elif resp.status_code == 503:
                errors += 1
                print(f"[legacy_miner] API locked (503). Waiting 2s before retry... (errors={errors})")
                time.sleep(2)
                continue

            else:
                errors += 1
                print(f"[legacy_miner] Unexpected status {resp.status_code}: {resp.text[:200]}")

        except requests.exceptions.RequestException as e:
            errors += 1
            print(f"[legacy_miner] Request error: {e}")
            time.sleep(2)
            continue

        time.sleep(1)  # ~1 request per second


def _save_results():
    """Persist current results to disk."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(
            {
                "client_id": CLIENT_ID,
                "total_extracted": len(results),
                "total_errors": errors,
                "elapsed_seconds": round(time.time() - start_time, 1),
                "records": results,
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _save_results()
        print(f"\n[legacy_miner] Stopped. Total: {len(results)} records, {errors} errors.")
