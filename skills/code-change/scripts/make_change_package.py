#!/usr/bin/env python3
"""Create a compact code-change deliverable zip.

The zip contains:
- a changelog markdown file at the archive root
- MANIFEST_CODE_CHANGE.json at the archive root
- changed source files under modified_code/<relative path>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

EXCLUDE_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
}


def _is_safe_relative(path: str) -> bool:
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts and path.strip() != ""


def _git_changed_files(repo: Path) -> list[str]:
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "diff", "--name-only", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _reject_excluded(paths: Iterable[str]) -> list[str]:
    allowed: list[str] = []
    for rel in paths:
        p = Path(rel)
        if any(part in EXCLUDE_PARTS for part in p.parts):
            continue
        allowed.append(rel)
    return allowed


def make_package(repo: Path, output: Path, changelog: Path, changed_files: list[str]) -> dict:
    repo = repo.resolve()
    output = output.resolve()
    changelog = changelog.resolve()

    if not repo.is_dir():
        raise SystemExit(f"repo is not a directory: {repo}")
    if not changelog.is_file():
        raise SystemExit(f"changelog file not found: {changelog}")

    if not changed_files:
        changed_files = _git_changed_files(repo)
    if not changed_files:
        raise SystemExit("no changed files provided and git diff did not find any")

    for rel in changed_files:
        if not _is_safe_relative(rel):
            raise SystemExit(f"unsafe relative path: {rel}")

    changed_files = _reject_excluded(changed_files)
    missing = [rel for rel in changed_files if not (repo / rel).is_file()]
    if missing:
        raise SystemExit("changed file(s) not found: " + ", ".join(missing))

    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "changelog": changelog.name,
        "changed_files": changed_files,
        "layout": {
            "changelog": changelog.name,
            "manifest": "MANIFEST_CODE_CHANGE.json",
            "code_root": "modified_code/",
        },
    }

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(changelog, changelog.name)
        zf.writestr("MANIFEST_CODE_CHANGE.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        for rel in changed_files:
            src = repo / rel
            if src.is_symlink():
                raise SystemExit(f"refusing to package symlink: {rel}")
            arcname = Path("modified_code") / rel
            zf.write(src, arcname.as_posix())

    manifest["output"] = str(output)
    manifest["size_bytes"] = output.stat().st_size
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a code-change deliverable zip")
    parser.add_argument("--repo", required=True, help="working project directory")
    parser.add_argument("--output", required=True, help="output zip path")
    parser.add_argument("--changelog", required=True, help="markdown changelog path")
    parser.add_argument("--changed-files", nargs="*", default=[], help="repo-relative changed files")
    args = parser.parse_args()

    manifest = make_package(
        repo=Path(args.repo),
        output=Path(args.output),
        changelog=Path(args.changelog),
        changed_files=list(args.changed_files),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
