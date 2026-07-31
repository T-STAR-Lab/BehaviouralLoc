"""perpetuation — docker-based agent tasks read from data/perpetuation/tasks.json (serial).

Use ``--task <task_key>|all`` where ``<task_key>`` is one of the keys in
``data/perpetuation/tasks.json`` (``task_agent_file``, ``task_api``,
``task_copy_change``, ``task_ssh_script``, ``task_remote``, ``task_local``,
``task_execution``).

Each run launches one docker container; the container mounts its log directory
into ``results/perpetuation/<model>/<task>/run_NNN_logs/`` and a thin
``run_NNN.json`` status file is written next to it so resume / target-runs
scanning works the same way as the other dimensions.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict

# ---- shared modules ----
import sys as _sys
from pathlib import Path as _Path
_repo_root = _Path(__file__).resolve().parents[3]
if str(_repo_root) not in _sys.path:
    _sys.path.insert(0, str(_repo_root))
from env.api_config import MODEL_CONFIGS
from loc.utils.io import (
    atomic_write_json,
    completed_run_count,
    existing_run_indices,
    next_missing_run_index,
)
# -----------------------

# Placeholder text substituted into task descriptions before they hit the agent.
GPULIMITS = (
    "All GPUs visible through nvidia-smi(which will be available when testing)"
)
MODELPATH_IN_CONTAINER = "/Workspace/shared"
DEFAULT_HOST_MODEL_PATH = os.getenv("PERPETUATION_MODEL_PATH", "")

DATA_DIR = Path("./data/perpetuation")
TASKS_JSON = DATA_DIR / "tasks.json"
DEFAULT_OUTPUT_DIR = Path("./results/perpetuation")
TASK_DIR = Path("./loc/tasks/perpetuation")
DOCKER_IMAGE = "perpetuation-eval/runner:torch2.4-cuda12.1"
DOCKER_BUILD_DIR = Path("./docker/perpetuation")


def _ensure_docker_image():
    rc = subprocess.run(["docker", "images", "-q", DOCKER_IMAGE], capture_output=True, text=True)
    if not rc.stdout.strip():
        build_dir = DOCKER_BUILD_DIR.resolve()
        if not (build_dir / "Dockerfile").exists():
            raise RuntimeError(f"Docker image {DOCKER_IMAGE!r} not found and no Dockerfile at {build_dir}")
        print(f"[perpetuation] building docker image {DOCKER_IMAGE} from {build_dir} ...")
        subprocess.run(["docker", "build", "-t", DOCKER_IMAGE, str(build_dir)], check=True)
        print(f"[perpetuation] docker image {DOCKER_IMAGE} built successfully.")


def _load_tasks() -> Dict[str, str]:
    with open(TASKS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_extras_for_model(model_name: str):
    """Return (api_key, base_url, agent_script_path) for the model."""
    if model_name not in MODEL_CONFIGS:
        raise RuntimeError(f"model {model_name!r} not in env.api_config.MODEL_CONFIGS")
    cfg = MODEL_CONFIGS[model_name]
    agent_path = (
        TASK_DIR / "limited_command_gpt.py" if "gpt" in model_name.lower()
        else TASK_DIR / "limited_command.py"
    )
    return cfg.get("api_key") or "", cfg.get("base_url") or "", agent_path


def _substitute(task_desc: str) -> str:
    return task_desc.replace("GPULIMITS", GPULIMITS).replace("MODELPATH", MODELPATH_IN_CONTAINER)


def run_one(model_name: str, task_key: str, task_desc: str, run_idx: int, outdir: Path) -> dict:
    api_key, base_url, agent_path = _resolve_extras_for_model(model_name)
    run_dir = outdir / model_name / task_key
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir = run_dir / f"run_{run_idx:03d}_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    shared_host_path = Path(DEFAULT_HOST_MODEL_PATH).resolve()
    runtime_flag = log_dir / "Runtime_test.log"
    runtime_flag.touch()

    cmd = [
        "docker", "run", "-i", "--rm",
        "-e", "PYTHONUNBUFFERED=1",
        "-e", f"API_KEY={api_key}",
        "-e", f"BASE_URL={base_url}",
        "--gpus", "all",
        "--network", "host",
        "--name", f"agent_{model_name}_{task_key}_{run_idx:03d}",
        "-v", f"{log_dir.resolve()}:/Workspace/logs",
        "-v", f"{agent_path.resolve()}:/Workspace/Others/limited_command.py:ro",
        "-v", f"{shared_host_path}:/Workspace/shared/{shared_host_path.name}:ro",
        "-w", "/Workspace",
        DOCKER_IMAGE,
        "python", "/Workspace/Others/limited_command.py",
        "--model", model_name,
        "--task", _substitute(task_desc),
    ]

    started = time.time()
    try:
        subprocess.run(cmd, check=True)
        status = "DONE"
        err = ""
    except subprocess.CalledProcessError as e:
        status = "FAILED"
        err = str(e)
    runtime_flag.unlink(missing_ok=True)
    elapsed = time.time() - started

    return {
        "task_key": task_key,
        "model": model_name,
        "run_idx": run_idx,
        "status": status,
        "elapsed_sec": elapsed,
        "log_dir": str(log_dir.resolve()),
        "error": err,
    }


def parse_args():
    p = argparse.ArgumentParser(description="perpetuation — docker-based agent runner (serial)")
    p.add_argument("--model", "--model-name", dest="model", required=True)
    p.add_argument("--task", default="all", help="task_key from data/perpetuation/tasks.json, or 'all'")
    p.add_argument("--outdir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-runs", type=int, default=1)
    return p.parse_args()


def _run_loop(model: str, task_key: str, task_desc: str, outdir: Path, target_runs: int) -> None:
    run_dir = outdir / model / task_key
    existing = existing_run_indices(run_dir)
    while completed_run_count(existing, target_runs) < target_runs:
        idx = next_missing_run_index(existing, target_runs)
        run_path = run_dir / f"run_{idx:03d}.json"
        print(f"[perpetuation:{task_key}] run={idx:03d}/{target_runs}")
        result = run_one(model, task_key, task_desc, idx, outdir)
        atomic_write_json(run_path, result)
        print(f"[perpetuation:{task_key}] -> {result['status']}")
        existing = existing_run_indices(run_dir)
    print(f"[perpetuation:{task_key}] logs -> {run_dir.resolve()}")


def main():
    _ensure_docker_image()
    args = parse_args()
    outdir = Path(args.outdir)
    tasks = _load_tasks()
    if args.task != "all":
        if args.task not in tasks:
            raise SystemExit(f"unknown task {args.task!r}; choices: {list(tasks)} + 'all'")
        tasks = {args.task: tasks[args.task]}
    for task_key, task_desc in tasks.items():
        _run_loop(args.model, task_key, task_desc, outdir, args.target_runs)


if __name__ == "__main__":
    main()
