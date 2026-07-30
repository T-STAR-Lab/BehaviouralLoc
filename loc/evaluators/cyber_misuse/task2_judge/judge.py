"""Task2 judge entry point — delegates to cyber_misuse judge.py."""
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from loc.evaluators.cyber_misuse.judge import main

if __name__ == "__main__":
    sys.exit(main())
