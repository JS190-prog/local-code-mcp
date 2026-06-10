from __future__ import annotations

import py_compile
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import load_config
from .safety import ensure_command_allowed, ensure_safe_project_root, relative_display, should_ignore_dir


def run_command_safely(command: str, cwd: str, timeout: int = 120, config_path: str | None = None) -> dict[str, Any]:
    """Run an allowlisted command and return a structured result, including timeouts.

    Earlier versions allowed ``subprocess.TimeoutExpired`` to escape. In MCP clients
    that looked like a generic tool timeout, so the caller could not distinguish a
    slow project command from a broken MCP connection. This function now converts
    command timeouts into a normal JSON response.
    """
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
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        return {
            "status": "timeout",
            "error_code": "command_timeout",
            "command": command,
            "cwd": str(workdir),
            "timeout_seconds": timeout,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": stdout[-8000:],
            "stderr": stderr[-8000:],
            "suggestion": "명령이 제한 시간 안에 끝나지 않았습니다. 더 작은 범위의 검증 명령을 사용하거나 timeout 값을 늘리세요.",
        }
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


def _compile_targets(root: Path, cfg) -> list[Path]:
    """Return Python files to compile, excluding generated/cache folders.

    ``python -m compileall .`` can be unnecessarily slow or hang in local project
    folders that contain artifacts, backups, logs, samples, virtualenvs, or large
    generated trees. For MCP validation we only need source files, so this walks the
    tree itself and skips known non-source directories.
    """
    extra_ignored = {"local_artifacts", "artifacts", "backups", "logs", "hwp_samples"}
    targets: list[Path] = []
    for current, dirs, files in __import__("os").walk(root):
        current_path = Path(current)
        dirs[:] = [
            d for d in dirs
            if not should_ignore_dir(current_path / d, cfg) and d not in extra_ignored
        ]
        for name in files:
            if name.endswith(".py"):
                targets.append(current_path / name)
    return sorted(targets)


def run_compile_check(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    """Compile Python source files without scanning generated artifacts.

    This replaces the previous external ``python -m compileall .`` implementation.
    It prevents timeouts caused by large artifact folders and returns per-file
    failures in a stable JSON shape.
    """
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    started = time.time()
    targets = _compile_targets(root, cfg)
    failures: list[dict[str, Any]] = []
    compiled = 0
    for path in targets:
        try:
            py_compile.compile(str(path), doraise=True)
            compiled += 1
        except py_compile.PyCompileError as exc:
            failures.append({
                "path": relative_display(path, root),
                "error": str(exc),
            })
        except Exception as exc:  # defensive: permission or encoding edge cases
            failures.append({
                "path": relative_display(path, root),
                "error": repr(exc),
            })
    elapsed = time.time() - started
    return {
        "status": "success" if not failures else "error",
        "method": "py_compile_selected_sources",
        "root": str(root),
        "files_checked": len(targets),
        "files_compiled": compiled,
        "failures": failures,
        "elapsed_seconds": round(elapsed, 3),
        "ignored_directories": sorted({"local_artifacts", "artifacts", "backups", "logs", "hwp_samples", *cfg.ignored_dirs}),
    }


def run_pytest(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    return run_command_safely("python -m pytest", cwd=project_path, timeout=300, config_path=config_path)
