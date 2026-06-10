from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import load_config
from .safety import SafetyError, allowed_root_for, ensure_safe_project_root, is_relative_to


def _find_git_marker(root: Path, allowed_root: Path) -> Path | None:
    """Find a .git directory/file without invoking git.

    Calling ``git status`` in a non-repository can be surprisingly slow on some
    Windows machines if Git walks parent folders or hits locked/network paths.
    A cheap marker check lets the MCP return a clear non-git result immediately.
    """
    current = root
    while True:
        marker = current / ".git"
        if marker.exists():
            return marker
        if current == allowed_root or current.parent == current or not is_relative_to(current.parent, allowed_root):
            return None
        current = current.parent


def _git(project_path: str, args: list[str], config_path: str | None = None, timeout: int = 30) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    allowed_root = allowed_root_for(root, cfg)
    marker = _find_git_marker(root, allowed_root)
    if marker is None:
        return {
            "status": "skipped",
            "error_code": "not_git_repository",
            "command": "git " + " ".join(args),
            "cwd": str(root),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "message": "해당 프로젝트 루트 또는 허용 루트 상위 범위에서 .git 디렉터리/파일을 찾지 못했습니다.",
        }

    command = [
        "git",
        "-c", "core.preloadindex=false",
        "-c", "core.fscache=false",
        "-c", "gc.auto=0",
        *args,
    ]
    env = os.environ.copy()
    env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_PAGER": "cat",
    })
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "status": "timeout",
            "error_code": "git_timeout",
            "command": "git " + " ".join(args),
            "cwd": str(root),
            "timeout_seconds": timeout,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
            "suggestion": "대형 저장소이거나 잠금 문제가 있을 수 있습니다. --untracked-files=no 상태 조회 또는 Git 저장소 잠금을 확인하세요.",
        }
    elapsed = time.time() - started
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "command": "git " + " ".join(args),
        "cwd": str(root),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-12000:],
        "stderr": proc.stderr[-12000:],
        "elapsed_seconds": round(elapsed, 3),
    }


def git_status(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    # ``--untracked-files=no`` avoids long scans of generated artifacts in local workspaces.
    return _git(project_path, ["status", "--short", "--untracked-files=no"], config_path=config_path, timeout=20)


def git_diff(project_path: str, staged: bool = False, config_path: str | None = None) -> dict[str, Any]:
    args = ["diff", "--no-ext-diff", "--no-color", "--staged"] if staged else ["diff", "--no-ext-diff", "--no-color"]
    return _git(project_path, args, config_path=config_path, timeout=30)


def git_changed_files(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    result = _git(project_path, ["status", "--porcelain", "--untracked-files=no"], config_path=config_path, timeout=20)
    files: list[str] = []
    if result.get("returncode") == 0:
        for line in result["stdout"].splitlines():
            if not line.strip():
                continue
            files.append(line[3:].strip())
    result["files"] = files
    return result


def git_create_branch(project_path: str, branch_name: str, config_path: str | None = None) -> dict[str, Any]:
    if not branch_name.startswith("ai-change/"):
        raise SafetyError("Branch name must start with ai-change/")
    return _git(project_path, ["checkout", "-b", branch_name], config_path=config_path, timeout=30)


def git_restore_file(project_path: str, rel_path: str, config_path: str | None = None) -> dict[str, Any]:
    if rel_path.startswith("/") or ".." in rel_path.replace("\\", "/").split("/"):
        raise SafetyError("Invalid relative path for git restore")
    return _git(project_path, ["restore", "--", rel_path], config_path=config_path, timeout=30)
