from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import load_config
from .safety import SafetyError, ensure_safe_project_root


def _tail(value: str | bytes | None, limit: int = 12000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return value[-limit:]


def _find_git_marker(root: Path) -> Path | None:
    current = root
    while True:
        marker = current / ".git"
        if marker.exists():
            return marker
        if current.parent == current:
            return None
        current = current.parent


def _clean_git_env() -> dict[str, str]:
    """Return a subprocess environment that avoids inherited Git context."""
    env = os.environ.copy()
    for key in [
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_PREFIX",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ]:
        env.pop(key, None)
    env.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_PAGER": "cat",
        "GIT_OPTIONAL_LOCKS": "0",
    })
    return env


def _git_executable(cfg) -> str:
    return getattr(cfg, "git_executable", "git") or "git"


def _git_command_label(executable: str, args: list[str]) -> str:
    return " ".join([executable, *args])


def _git(project_path: str, args: list[str], config_path: str | None = None, timeout: int = 30) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    marker = _find_git_marker(root)
    executable = _git_executable(cfg)
    if marker is None:
        return {
            "status": "skipped",
            "error_code": "not_git_repository",
            "command": _git_command_label(executable, args),
            "cwd": str(root),
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "message": "해당 경로 또는 상위 경로에서 .git 디렉터리/파일을 찾지 못했습니다.",
        }

    command = [executable, *args]
    env = _clean_git_env()
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
        return {
            "status": "timeout",
            "error_code": "git_timeout",
            "command": _git_command_label(executable, args),
            "cwd": str(root),
            "timeout_seconds": timeout,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": _tail(exc.stdout),
            "stderr": _tail(exc.stderr),
            "suggestion": "MCP 서버 프로세스의 Git 실행 환경 문제일 수 있습니다. mcp_git_diagnose로 PATH, git_executable, GIT_* 환경변수를 확인하세요.",
        }
    except FileNotFoundError as exc:
        return {
            "status": "error",
            "error_code": "git_not_found",
            "command": _git_command_label(executable, args),
            "cwd": str(root),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "suggestion": "Git이 PATH에 등록되어 있는지 확인하거나 config.json의 git_executable에 git.exe 전체 경로를 지정하세요.",
        }
    except Exception as exc:
        return {
            "status": "error",
            "error_code": "git_exception",
            "command": _git_command_label(executable, args),
            "cwd": str(root),
            "returncode": None,
            "stdout": "",
            "stderr": repr(exc),
        }
    elapsed = time.time() - started
    return {
        "status": "success" if proc.returncode == 0 else "error",
        "command": _git_command_label(executable, args),
        "cwd": str(root),
        "returncode": proc.returncode,
        "stdout": _tail(proc.stdout),
        "stderr": _tail(proc.stderr),
        "elapsed_seconds": round(elapsed, 3),
    }


def git_diagnose(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    """Diagnose Git execution from inside the MCP server process."""
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    executable = _git_executable(cfg)
    marker = _find_git_marker(root)
    env = _clean_git_env()
    inherited_git_env = {key: value for key, value in os.environ.items() if key.startswith("GIT_")}
    started = time.time()
    checks: list[dict[str, Any]] = []

    def run_check(name: str, args: list[str], timeout: int = 10) -> None:
        check_started = time.time()
        command = [executable, *args]
        try:
            proc = subprocess.run(
                command,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            checks.append({
                "name": name,
                "status": "success" if proc.returncode == 0 else "error",
                "command": _git_command_label(executable, args),
                "returncode": proc.returncode,
                "stdout": _tail(proc.stdout, 2000),
                "stderr": _tail(proc.stderr, 2000),
                "elapsed_seconds": round(time.time() - check_started, 3),
            })
        except subprocess.TimeoutExpired as exc:
            checks.append({
                "name": name,
                "status": "timeout",
                "command": _git_command_label(executable, args),
                "timeout_seconds": timeout,
                "stdout": _tail(exc.stdout, 2000),
                "stderr": _tail(exc.stderr, 2000),
                "elapsed_seconds": round(time.time() - check_started, 3),
            })
        except FileNotFoundError as exc:
            checks.append({
                "name": name,
                "status": "error",
                "error_code": "git_not_found",
                "command": _git_command_label(executable, args),
                "stderr": str(exc),
                "elapsed_seconds": round(time.time() - check_started, 3),
            })
        except Exception as exc:
            checks.append({
                "name": name,
                "status": "error",
                "error_code": "git_exception",
                "command": _git_command_label(executable, args),
                "stderr": repr(exc),
                "elapsed_seconds": round(time.time() - check_started, 3),
            })

    run_check("git_version", ["--version"], timeout=10)
    run_check("git_status", ["status", "--short", "--untracked-files=no"], timeout=10)

    return {
        "status": "success" if all(item.get("status") == "success" for item in checks) else "error",
        "cwd": str(root),
        "git_marker": str(marker) if marker else None,
        "git_executable": executable,
        "git_on_path": shutil.which("git"),
        "inherited_git_env_keys": sorted(inherited_git_env),
        "cleaned_git_env_removed": sorted(inherited_git_env),
        "checks": checks,
        "elapsed_seconds": round(time.time() - started, 3),
        "suggestion": "If checks timeout but PowerShell git is fast, set git_executable in config.json to the full Git path, for example C:/Program Files/Git/cmd/git.exe.",
    }


def _validate_git_rel_path(rel_path: str) -> str:
    normalized = str(rel_path).replace("\\", "/").strip()
    if not normalized:
        raise SafetyError("Git path is empty")
    parts = normalized.split("/")
    if normalized.startswith("/") or normalized.startswith("-") or ".." in parts:
        raise SafetyError(f"Invalid git relative path: {rel_path}")
    return normalized


def _normalize_file_list(files: list[str] | str | None) -> list[str]:
    if files is None:
        return []
    if isinstance(files, str):
        files = [files]
    return [_validate_git_rel_path(item) for item in files]


def _validate_commit_message(message: str) -> str:
    msg = (message or "").strip()
    if not msg:
        raise SafetyError("Commit message is required")
    if "\n" in msg or "\r" in msg:
        raise SafetyError("Commit message must be a single line")
    if len(msg) > 200:
        raise SafetyError("Commit message must be 200 characters or fewer")
    return msg


def git_status(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    return _git(project_path, ["status", "--short", "--untracked-files=no"], config_path=config_path, timeout=20)


def git_diff(project_path: str, staged: bool = False, config_path: str | None = None) -> dict[str, Any]:
    args = ["diff", "--no-ext-diff", "--no-color", "--staged"] if staged else ["diff", "--no-ext-diff", "--no-color"]
    return _git(project_path, args, config_path=config_path, timeout=30)


def git_changed_files(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    result = _git(project_path, ["status", "--porcelain", "--untracked-files=no"], config_path=config_path, timeout=20)
    files: list[str] = []
    if result.get("returncode") == 0:
        for line in result.get("stdout", "").splitlines():
            if not line.strip():
                continue
            files.append(line[3:].strip())
    result["files"] = files
    return result


def git_add(project_path: str, files: list[str] | str, config_path: str | None = None) -> dict[str, Any]:
    safe_files = _normalize_file_list(files)
    if not safe_files:
        return {
            "status": "error",
            "error_code": "no_files",
            "message": "No files were provided for git add.",
        }
    return _git(project_path, ["add", "--", *safe_files], config_path=config_path, timeout=60)


def git_commit(project_path: str, message: str, config_path: str | None = None) -> dict[str, Any]:
    msg = _validate_commit_message(message)
    return _git(project_path, ["commit", "-m", msg], config_path=config_path, timeout=120)


def git_commit_files(project_path: str, files: list[str] | str, message: str, config_path: str | None = None) -> dict[str, Any]:
    add_result = git_add(project_path, files, config_path=config_path)
    if add_result.get("status") != "success":
        return {
            "status": "error",
            "stage": "git_add",
            "add_result": add_result,
        }

    commit_result = git_commit(project_path, message, config_path=config_path)
    return {
        "status": commit_result.get("status"),
        "stage": "git_commit",
        "add_result": add_result,
        "commit_result": commit_result,
    }


def git_create_branch(project_path: str, branch_name: str, config_path: str | None = None) -> dict[str, Any]:
    if not branch_name.startswith("ai-change/"):
        raise SafetyError("Branch name must start with ai-change/")
    return _git(project_path, ["checkout", "-b", branch_name], config_path=config_path, timeout=30)


def git_restore_file(project_path: str, rel_path: str, config_path: str | None = None) -> dict[str, Any]:
    safe_rel_path = _validate_git_rel_path(rel_path)
    return _git(project_path, ["restore", "--", safe_rel_path], config_path=config_path, timeout=30)
