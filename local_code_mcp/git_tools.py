from __future__ import annotations

import subprocess
from typing import Any

from .config import load_config
from .safety import SafetyError, ensure_safe_project_root


def _git(project_path: str, args: list[str], config_path: str | None = None, timeout: int = 120) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    proc = subprocess.run(
        ["git", *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "command": "git " + " ".join(args),
        "cwd": str(root),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
    }


def git_status(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    return _git(project_path, ["status", "--short"], config_path=config_path)


def git_diff(project_path: str, staged: bool = False, config_path: str | None = None) -> dict[str, Any]:
    args = ["diff", "--staged"] if staged else ["diff"]
    return _git(project_path, args, config_path=config_path)


def git_changed_files(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    result = _git(project_path, ["status", "--porcelain"], config_path=config_path)
    files: list[str] = []
    if result["returncode"] == 0:
        for line in result["stdout"].splitlines():
            if not line.strip():
                continue
            files.append(line[3:].strip())
    result["files"] = files
    return result


def git_create_branch(project_path: str, branch_name: str, config_path: str | None = None) -> dict[str, Any]:
    if not branch_name.startswith("ai-change/"):
        raise SafetyError("Branch name must start with ai-change/")
    return _git(project_path, ["checkout", "-b", branch_name], config_path=config_path)


def git_restore_file(project_path: str, rel_path: str, config_path: str | None = None) -> dict[str, Any]:
    if rel_path.startswith("/") or ".." in rel_path.replace("\\", "/").split("/"):
        raise SafetyError("Invalid relative path for git restore")
    return _git(project_path, ["restore", "--", rel_path], config_path=config_path)
