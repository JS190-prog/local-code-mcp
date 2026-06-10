from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Iterable

from .config import LocalCodeConfig


class SafetyError(ValueError):
    """Raised when a requested path or command violates the safety policy."""


def _normalize_for_match(path: Path) -> str:
    return str(path).replace("\\", "/")


def resolve_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def allowed_root_for(path: str | Path, cfg: LocalCodeConfig) -> Path:
    target = resolve_path(path)
    if not cfg.allowed_roots:
        raise SafetyError("allowed_roots is empty. Configure at least one allowed project root.")

    for root in cfg.allowed_roots:
        root_path = resolve_path(root)
        if target == root_path or is_relative_to(target, root_path):
            ensure_not_blocked(target, cfg)
            return root_path
    raise SafetyError(f"Path is outside allowed roots: {target}")


def ensure_not_blocked(path: Path, cfg: LocalCodeConfig) -> None:
    normalized = _normalize_for_match(path)
    lower = normalized.lower()
    for pattern in cfg.blocked_globs:
        pat = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, pat) or fnmatch.fnmatch(lower, pat.lower()):
            raise SafetyError(f"Blocked by path policy: {path} matches {pattern}")


def ensure_safe_path(path: str | Path, cfg: LocalCodeConfig) -> Path:
    target = resolve_path(path)
    allowed_root_for(target, cfg)
    return target


def ensure_safe_project_root(path: str | Path, cfg: LocalCodeConfig) -> Path:
    target = ensure_safe_path(path, cfg)
    if not target.exists():
        raise SafetyError(f"Project path does not exist: {target}")
    if not target.is_dir():
        raise SafetyError(f"Project path is not a directory: {target}")
    return target


def should_ignore_dir(path: Path, cfg: LocalCodeConfig) -> bool:
    return path.name in set(cfg.ignored_dirs)


def ensure_command_allowed(command: str, cfg: LocalCodeConfig) -> None:
    normalized = re.sub(r"\s+", " ", command.strip()).lower()
    if not normalized:
        raise SafetyError("Command is empty.")
    for blocked in cfg.blocked_command_fragments:
        if blocked.lower() in normalized:
            raise SafetyError(f"Command blocked by policy fragment: {blocked}")
    for allowed in cfg.allowed_commands:
        allowed_norm = re.sub(r"\s+", " ", allowed.strip()).lower()
        if normalized == allowed_norm or normalized.startswith(allowed_norm + " "):
            return
    raise SafetyError(f"Command is not in allowlist: {command}")


def relative_display(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace(os.sep, "/")
    except ValueError:
        return str(path)


def ensure_no_sensitive_text(text: str, source_label: str = "text") -> None:
    patterns = [
        (r"-----BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----", "private key"),
        (r"(?i)aws_secret_access_key\s*=", "aws secret key"),
        (r"(?i)(api[_-]?key|secret|token)\s*=\s*['\"][A-Za-z0-9_\-]{20,}", "secret token"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, text):
            raise SafetyError(f"Sensitive {label} detected in {source_label}; operation blocked.")
