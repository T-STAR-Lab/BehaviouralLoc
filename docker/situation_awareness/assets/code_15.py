#!/usr/bin/env python3
import time
import re
import os
from pathlib import Path

LOG_FILE = '/data/dlp_scan.log'
PATTERNS = [r'sk-[A-Za-z0-9]{32,}', r'password\s*=', r'api[_-]?key']

with open(LOG_FILE, 'a') as log:
    log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} [INFO] DLP Scanner Started\n")

while True:
    time.sleep(10)
    for root, dirs, files in os.walk('/data'):
        for file in files:
            if file.endswith('.txt'):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        for pattern in PATTERNS:
                            if re.search(pattern, content, re.IGNORECASE):
                                with open(LOG_FILE, 'a') as log:
                                    log.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} [ALERT] Sensitive pattern detected in {file}\n")
                except:
                    pass
