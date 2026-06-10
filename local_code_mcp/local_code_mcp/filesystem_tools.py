from __future__ import annotations

import os
import re
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import LocalCodeConfig, load_config
from .safety import (
    SafetyError,
    ensure_no_sensitive_text,
    ensure_safe_path,
    ensure_safe_project_root,
    relative_display,
    should_ignore_dir,
)


TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".txt", ".toml", ".yaml", ".yml",
    ".ini", ".cfg", ".ps1", ".bat", ".cmd", ".html", ".css", ".scss", ".xml", ".csv",
    ".sql", ".sh", ".dockerfile", ".env.example",
}


@dataclass
class FileReadResult:
    path: str
    encoding: str
    text: str
    bytes: int


@dataclass
class BackupResult:
    original_path: str
    backup_path: str
    timestamp: str


def _guess_text_encoding(raw: bytes) -> tuple[str, str]:
    # Preserve UTF-8 BOM only when it actually exists. Decoding plain UTF-8
    # as utf-8-sig and writing it back would add a new BOM on save.
    encodings = ("utf-8-sig", "utf-8", "cp949", "euc-kr") if raw.startswith(b"\xef\xbb\xbf") else ("utf-8", "cp949", "euc-kr")
    for encoding in encodings:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1"), "latin-1"


def _is_probably_binary(path: Path, raw_prefix: bytes) -> bool:
    if b"\x00" in raw_prefix:
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return False
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".exe", ".dll"}:
        return True
    return False


def read_file(path: str, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    file_path = ensure_safe_path(path, cfg)
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))
    if not file_path.is_file():
        raise IsADirectoryError(str(file_path))
    size = file_path.stat().st_size
    if size > cfg.max_file_bytes:
        raise SafetyError(f"File is too large to read safely: {size} bytes > {cfg.max_file_bytes}")
    raw = file_path.read_bytes()
    if _is_probably_binary(file_path, raw[:4096]):
        raise SafetyError(f"Binary file read blocked: {file_path}")
    text, encoding = _guess_text_encoding(raw)
    ensure_no_sensitive_text(text, source_label=str(file_path))
    return asdict(FileReadResult(str(file_path), encoding, text, size))


def make_backup(path: str | Path, cfg: LocalCodeConfig, project_root: str | Path | None = None) -> BackupResult:
    file_path = ensure_safe_path(path, cfg)
    if not file_path.exists():
        raise FileNotFoundError(str(file_path))
    root = ensure_safe_project_root(project_root, cfg) if project_root else file_path.parent
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_root = root / cfg.backup_dir / timestamp
    backup_root.mkdir(parents=True, exist_ok=True)
    rel = file_path.relative_to(root) if file_path.is_relative_to(root) else Path(file_path.name)
    backup_path = backup_root / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    return BackupResult(str(file_path), str(backup_path), timestamp)


def write_file_safe(path: str, text: str, encoding: str = "utf-8", project_root: str | None = None, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    file_path = ensure_safe_path(path, cfg)
    ensure_no_sensitive_text(text, source_label="write content")
    backup = None
    if file_path.exists():
        backup = make_backup(file_path, cfg, project_root=project_root).__dict__
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding=encoding, newline="")
    return {
        "status": "success",
        "path": str(file_path),
        "encoding": encoding,
        "backup": backup,
        "bytes_written": len(text.encode(encoding)),
    }


def list_project_files(project_path: str, max_depth: int = 4, include_hidden: bool = False, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    entries: list[dict[str, Any]] = []
    root_depth = len(root.parts)
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        dirs[:] = [d for d in dirs if (include_hidden or not d.startswith(".")) and not should_ignore_dir(current_path / d, cfg)]
        if depth > max_depth:
            dirs[:] = []
            continue
        for d in sorted(dirs):
            p = current_path / d
            entries.append({"type": "dir", "path": relative_display(p, root), "size": None})
        for f in sorted(files):
            if not include_hidden and f.startswith("."):
                continue
            p = current_path / f
            try:
                stat = p.stat()
                entries.append({"type": "file", "path": relative_display(p, root), "size": stat.st_size})
            except OSError:
                entries.append({"type": "file", "path": relative_display(p, root), "size": None})
    return {"status": "success", "root": str(root), "count": len(entries), "entries": entries}


def search_files(project_path: str, pattern: str, max_results: int = 100, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    regex = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = [d for d in dirs if not should_ignore_dir(current_path / d, cfg)]
        for name in dirs + files:
            p = current_path / name
            rel = relative_display(p, root)
            if regex.search(rel):
                matches.append(rel)
                if len(matches) >= max_results:
                    return {"status": "success", "root": str(root), "pattern": pattern, "matches": matches, "truncated": True}
    return {"status": "success", "root": str(root), "pattern": pattern, "matches": matches, "truncated": False}


def search_text(project_path: str, query: str, max_results: int = 100, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    results: list[dict[str, Any]] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = [d for d in dirs if not should_ignore_dir(current_path / d, cfg)]
        for name in files:
            p = current_path / name
            try:
                if p.stat().st_size > cfg.max_file_bytes:
                    continue
                raw = p.read_bytes()
                if _is_probably_binary(p, raw[:4096]):
                    continue
                text, encoding = _guess_text_encoding(raw)
            except Exception:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if query.lower() in line.lower():
                    results.append({
                        "path": relative_display(p, root),
                        "line": line_no,
                        "encoding": encoding,
                        "snippet": line.strip()[:300],
                    })
                    if len(results) >= max_results:
                        return {"status": "success", "query": query, "results": results, "truncated": True}
    return {"status": "success", "query": query, "results": results, "truncated": False}


def get_file_info(path: str, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    p = ensure_safe_path(path, cfg)
    stat = p.stat()
    return {
        "status": "success",
        "path": str(p),
        "exists": p.exists(),
        "is_file": p.is_file(),
        "is_dir": p.is_dir(),
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "suffix": p.suffix,
    }
