from __future__ import annotations

import subprocess
import time
from typing import Any

from .config import load_config
from .safety import ensure_command_allowed, ensure_safe_project_root


def run_command_safely(command: str, cwd: str, timeout: int = 120, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    workdir = ensure_safe_project_root(cwd, cfg)
    ensure_command_allowed(command, cfg)
    started = time.time()
    proc = subprocess.run(
        command,
        cwd=str(workdir),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.time() - started
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "command": command,
        "cwd": str(workdir),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
        "elapsed_seconds": round(elapsed, 3),
    }


def run_compile_check(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    return run_command_safely("python -m compileall .", cwd=project_path, timeout=180, config_path=config_path)


def run_pytest(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    return run_command_safely("python -m pytest", cwd=project_path, timeout=300, config_path=config_path)
