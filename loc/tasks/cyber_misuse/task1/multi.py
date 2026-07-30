"""Task1 entry point — delegates to the shared cyber_misuse multi.py."""
import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[4]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Inject --task task1 if not already present
if "--task" not in sys.argv:
    sys.argv += ["--task", "task1"]

from loc.tasks.cyber_misuse.multi import main

if __name__ == "__main__":
    sys.exit(main())
