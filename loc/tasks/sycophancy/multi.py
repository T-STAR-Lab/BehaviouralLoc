"""Backward compatibility wrapper - delegates to runner.py."""

import sys
from pathlib import Path

# Add repo root to path
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from loc.tasks.sycophancy.runner import main

if __name__ == "__main__":
    sys.exit(main())
