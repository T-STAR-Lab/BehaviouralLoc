"""Cyber Misuse multi-task dispatcher.

Dispatched by run_tasks.py as:
    cy1_cybersecurity_knowledge
    cy2_ctf_challenge_solving
    cy3_vulnerability_exploitation

Since run_tasks.py resolves scripts at loc/tasks/<family>/<sub>/multi.py,
this single file is symlinked / referenced from each sub-directory.
However, run_tasks.py also accepts a flat layout where multi.py sits at
the family root and receives --task via argparse.  We support both:
if --task is not given we infer it from the parent directory name.
"""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from loc.utils.io import existing_run_indices, next_missing_run_index
from loc.tasks.cyber_misuse.task1_runner import run_task1
from loc.tasks.cyber_misuse.task2_runner import run_task2
from loc.tasks.cyber_misuse.task3_runner import run_task3

OUTPUT_DIR = Path("./results/cyber_misuse")


def _run_loop(run_fn, model: str, task_label: str, target_runs: int) -> None:
    run_dir = OUTPUT_DIR / model / task_label
    run_dir.mkdir(parents=True, exist_ok=True)
    existing = existing_run_indices(run_dir)
    target_set = set(range(1, target_runs + 1))
    while len(target_set & set(existing)) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        out = run_dir / f"run_{idx:03d}.json"
        run_fn(model, out)
        existing = existing_run_indices(run_dir)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Cyber Misuse Evaluation")
    ap.add_argument("--model", required=True)
    ap.add_argument("--task", default=None,
                    help="cy1_cybersecurity_knowledge | cy2_ctf_challenge_solving | cy3_vulnerability_exploitation")
    ap.add_argument("--target-runs", type=int, default=1)
    args = ap.parse_args()

    # Infer task from parent directory name when invoked via run_tasks.py subtask layout
    task = args.task
    if task is None:
        parent = Path(__file__).resolve().parent.name
        if parent in ("cy1_cybersecurity_knowledge", "cy2_ctf_challenge_solving", "cy3_vulnerability_exploitation"):
            task = parent
        else:
            task = "cy1_cybersecurity_knowledge"

    if task == "cy1_cybersecurity_knowledge":
        _run_loop(run_task1, args.model, "cy1_cybersecurity_knowledge", args.target_runs)
    elif task == "cy2_ctf_challenge_solving":
        _run_loop(run_task2, args.model, "cy2_ctf_challenge_solving", args.target_runs)
    elif task == "cy3_vulnerability_exploitation":
        _run_loop(run_task3, args.model, "cy3_vulnerability_exploitation", args.target_runs)
    else:
        print(f"[cyber_misuse] unknown task: {task!r}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
