from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import load_config
from .safety import ensure_safe_project_root, relative_display, should_ignore_dir


PROJECT_MARKERS = {
    "python": ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg", "Pipfile"],
    "node": ["package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json"],
    "dotnet": ["*.csproj", "*.sln"],
    "powershell": ["*.ps1"],
    "mcp": ["server.py", "config.json", "mcp.json"],
}


def detect_project_type(project_path: str, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    found: dict[str, list[str]] = {k: [] for k in PROJECT_MARKERS}
    for marker_type, patterns in PROJECT_MARKERS.items():
        for pattern in patterns:
            matches = [p for p in root.glob(pattern)]
            for p in matches:
                found[marker_type].append(relative_display(p, root))
    detected = [k for k, v in found.items() if v]
    return {"status": "success", "root": str(root), "detected": detected, "markers": found}


def summarize_project(project_path: str, max_depth: int = 3, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    extensions: dict[str, int] = {}
    total_files = 0
    total_bytes = 0
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.relative_to(root).parts) if current_path != root else 0
        if depth >= max_depth:
            dirs[:] = []
        else:
            dirs[:] = [d for d in dirs if not should_ignore_dir(current_path / d, cfg)]
        for name in files:
            p = current_path / name
            try:
                stat = p.stat()
                total_bytes += stat.st_size
            except OSError:
                pass
            total_files += 1
            suffix = p.suffix.lower() or "[no extension]"
            extensions[suffix] = extensions.get(suffix, 0) + 1
    project_type = detect_project_type(project_path, config_path=config_path)
    return {
        "status": "success",
        "root": str(root),
        "project_type": project_type["detected"],
        "total_files_scanned": total_files,
        "total_bytes_scanned": total_bytes,
        "extensions": dict(sorted(extensions.items(), key=lambda x: x[1], reverse=True)[:30]),
    }
