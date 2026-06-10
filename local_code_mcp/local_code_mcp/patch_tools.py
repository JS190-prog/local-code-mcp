from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from .config import load_config
from .filesystem_tools import _guess_text_encoding, _is_probably_binary, make_backup
from .safety import SafetyError, ensure_no_sensitive_text, ensure_safe_path


def _load_text(path: Path, max_file_bytes: int) -> tuple[str, str]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    if not path.is_file():
        raise IsADirectoryError(str(path))
    if path.stat().st_size > max_file_bytes:
        raise SafetyError(f"File is too large to patch safely: {path.stat().st_size} bytes")
    raw = path.read_bytes()
    if _is_probably_binary(path, raw[:4096]):
        raise SafetyError(f"Binary file patch blocked: {path}")
    text, encoding = _guess_text_encoding(raw)
    ensure_no_sensitive_text(text, source_label=str(path))
    return text, encoding


def _make_diff(original: str, modified: str, fromfile: str, tofile: str) -> str:
    if original == modified:
        return ""
    return "\n".join(difflib.unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile=fromfile,
        tofile=tofile,
        lineterm="",
    )) + "\n"


def replace_in_file(
    path: str,
    replacements: list[dict[str, Any]] | str,
    dry_run: bool = True,
    project_root: str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    """Replace exact text snippets in a file with backup and diff output.

    replacements may be a JSON string or a list of dictionaries:
    [{"old": "...", "new": "...", "replace_all": false}]
    """
    cfg = load_config(config_path)
    file_path = ensure_safe_path(path, cfg)
    if isinstance(replacements, str):
        replacements = json.loads(replacements)
    original, encoding = _load_text(file_path, cfg.max_file_bytes)
    modified = original
    changes: list[dict[str, Any]] = []

    for idx, repl in enumerate(replacements, start=1):
        old = repl.get("old")
        new = repl.get("new")
        replace_all = bool(repl.get("replace_all", False))
        if old is None or new is None:
            raise ValueError(f"Replacement #{idx} must include old and new keys")
        ensure_no_sensitive_text(str(new), source_label=f"replacement #{idx}")
        count = modified.count(old)
        if count == 0:
            changes.append({"index": idx, "status": "not_found", "count": 0})
            continue
        if replace_all:
            modified = modified.replace(old, new)
            applied = count
        else:
            modified = modified.replace(old, new, 1)
            applied = 1
        changes.append({"index": idx, "status": "matched", "count": count, "applied": applied})

    diff = _make_diff(original, modified, str(file_path), str(file_path))
    result: dict[str, Any] = {
        "status": "dry_run" if dry_run else "success",
        "path": str(file_path),
        "encoding": encoding,
        "changed": original != modified,
        "changes": changes,
        "diff": diff,
    }
    if dry_run:
        return result
    if original == modified:
        result["status"] = "no_change"
        return result
    backup = make_backup(file_path, cfg, project_root=project_root).__dict__
    file_path.write_text(modified, encoding=encoding, newline="")
    result["backup"] = backup
    result["bytes_written"] = len(modified.encode(encoding, errors="replace"))
    return result


def restore_from_backup(backup_path: str, original_path: str, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    backup = ensure_safe_path(backup_path, cfg)
    original = ensure_safe_path(original_path, cfg)
    if not backup.exists():
        raise FileNotFoundError(str(backup))
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_bytes(backup.read_bytes())
    return {"status": "success", "restored": str(original), "from": str(backup)}
