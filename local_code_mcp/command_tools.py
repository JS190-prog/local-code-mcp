from __future__ import annotations

import os
import py_compile
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import load_config
from .safety import ensure_command_allowed, ensure_safe_project_root


def _tail(value: str | bytes | None, limit: int = 8000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return value[-limit:]


def _python_executable(root: Path) -> str:
    """Prefer the project's virtualenv Python when it exists."""
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / "venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
        root / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return "python"


def run_command_safely(command: str, cwd: str, timeout: int = 120, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    workdir = ensure_safe_project_root(cwd, cfg)
    ensure_command_allowed(command, cfg)
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(workdir),
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        return {
            "status": "timeout",
            "error_code": "command_timeout",
            "command": command,
            "cwd": str(workdir),
            "timeout_seconds": timeout,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": _tail(exc.stdout),
            "stderr": _tail(exc.stderr),
            "suggestion": "명령이 제한 시간 안에 끝나지 않았습니다. 범위를 줄이거나 timeout 값을 늘리세요.",
        }
    elapsed = time.time() - started
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "command": command,
        "cwd": str(workdir),
        "returncode": proc.returncode,
        "stdout": _tail(proc.stdout),
        "stderr": _tail(proc.stderr),
        "elapsed_seconds": round(elapsed, 3),
    }


def _compile_targets(root: Path, cfg) -> list[Path]:
    """Compile only source files, skipping generated/cache/artifact directories."""
    ignored = set(cfg.ignored_dirs) | {"local_artifacts", "artifacts", "backups", "logs", "hwp_samples"}
    targets: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ignored]
        current_path = Path(current)
        for name in files:
            if name.endswith(".py"):
                targets.append(current_path / name)
    return sorted(targets)


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path)


def run_compile_check(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    """Run a lightweight Python syntax check without scanning virtualenvs/artifacts."""
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    started = time.time()
    targets = _compile_targets(root, cfg)
    failures: list[dict[str, str]] = []
    for path in targets:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            failures.append({"path": _rel(path, root), "error": str(exc)})
        except Exception as exc:
            failures.append({"path": _rel(path, root), "error": repr(exc)})
    elapsed = time.time() - started
    return {
        "status": "success" if not failures else "error",
        "method": "py_compile_selected_sources",
        "root": str(root),
        "files_checked": len(targets),
        "failures": failures,
        "elapsed_seconds": round(elapsed, 3),
        "ignored_directories": sorted(set(cfg.ignored_dirs) | {"local_artifacts", "artifacts", "backups", "logs", "hwp_samples"}),
    }


def run_pytest(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    """Run pytest with the project virtualenv Python when available."""
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    python_exe = _python_executable(root)
    command = [python_exe, "-m", "pytest"]
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.time() - started
        return {
            "status": "timeout",
            "error_code": "pytest_timeout",
            "command": " ".join(command),
            "cwd": str(root),
            "python": python_exe,
            "timeout_seconds": 300,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": _tail(exc.stdout),
            "stderr": _tail(exc.stderr),
            "suggestion": "테스트가 제한 시간 안에 끝나지 않았습니다. 특정 테스트 파일만 실행해 보세요.",
        }
    elapsed = time.time() - started
    stderr = _tail(proc.stderr)
    stdout = _tail(proc.stdout)
    missing_pytest = proc.returncode != 0 and "No module named pytest" in (stdout + stderr)
    return {
        "status": "skipped" if missing_pytest else ("success" if proc.returncode == 0 else "error"),
        "error_code": "pytest_not_installed" if missing_pytest else None,
        "command": " ".join(command),
        "cwd": str(root),
        "python": python_exe,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_seconds": round(elapsed, 3),
        "suggestion": "프로젝트 가상환경에 pytest를 설치하거나 requirements/test extra를 설치하세요." if missing_pytest else None,
    }
