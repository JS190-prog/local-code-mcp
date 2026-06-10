from __future__ import annotations

import json
import os
import time
import zipfile
from pathlib import Path
from typing import Any

from .config import load_config
from .safety import ensure_safe_path, ensure_safe_project_root, relative_display


CHANGELOG_TEMPLATE = """# {title}

## 1. 작업 개요
- 작업일: {timestamp}
- 대상 폴더: `{project_path}`
- 요청 내용: {request_summary}

## 2. 수정 파일 목록
{changed_file_table}

## 3. 주요 변경 내용
{change_summary}

## 4. 검증 결과
{test_result_table}

## 5. 주의사항
{notes}

## 6. 롤백 방법
- Git 저장소인 경우 `git diff` 확인 후 `git restore <파일>`로 복원합니다.
- 백업이 생성된 경우 `local_artifacts/backups/` 아래의 백업 파일을 원래 위치로 복사합니다.
"""


def _table(rows: list[list[str]], headers: list[str]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for row in rows:
        out.append("| " + " | ".join(str(c).replace("\n", "<br>") for c in row) + " |")
    return "\n".join(out)


def generate_changelog_md(
    project_path: str,
    output_path: str | None = None,
    title: str = "Local Code MCP 변경사항 보고서",
    request_summary: str = "코드 수정 및 검증",
    changed_files: list[str] | str | None = None,
    change_summary: str = "- 수정 내용을 확인한 뒤 필요한 내용을 보완하세요.",
    test_results: list[dict[str, Any]] | str | None = None,
    notes: str = "- 자동 생성 문서입니다. 실제 배포 전 수동 검토를 권장합니다.",
    config_path: str | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    if isinstance(changed_files, str):
        try:
            changed_files = json.loads(changed_files)
        except json.JSONDecodeError:
            changed_files = [changed_files]
    changed_files = changed_files or []
    if isinstance(test_results, str):
        try:
            test_results = json.loads(test_results)
        except json.JSONDecodeError:
            test_results = [{"name": "검증", "status": "unknown", "detail": test_results}]
    test_results = test_results or []

    changed_rows = [[f, "수정/생성", "작업 결과 파일"] for f in changed_files] or [["-", "-", "변경 파일 정보 없음"]]
    test_rows = [[str(r.get("name", r.get("command", "검증"))), str(r.get("status", "unknown")), str(r.get("detail", r.get("returncode", "")))] for r in test_results]
    if not test_rows:
        test_rows = [["-", "-", "검증 결과 없음"]]

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    content = CHANGELOG_TEMPLATE.format(
        title=title,
        timestamp=timestamp,
        project_path=str(root),
        request_summary=request_summary,
        changed_file_table=_table(changed_rows, ["파일", "변경 유형", "설명"]),
        change_summary=change_summary,
        test_result_table=_table(test_rows, ["검증 항목", "결과", "세부내용"]),
        notes=notes,
    )

    if output_path:
        out = ensure_safe_path(output_path, cfg)
    else:
        out = root / cfg.output_dir / f"CHANGELOG_{time.strftime('%Y%m%d_%H%M%S')}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return {"status": "success", "path": str(out), "bytes": out.stat().st_size, "content": content}


def create_change_zip(
    project_path: str,
    output_zip: str | None = None,
    include_files: list[str] | str | None = None,
    include_patterns: list[str] | str | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    if isinstance(include_files, str):
        try:
            include_files = json.loads(include_files)
        except json.JSONDecodeError:
            include_files = [include_files]
    if isinstance(include_patterns, str):
        try:
            include_patterns = json.loads(include_patterns)
        except json.JSONDecodeError:
            include_patterns = [include_patterns]
    include_files = include_files or []
    include_patterns = include_patterns or []

    if output_zip:
        zip_path = ensure_safe_path(output_zip, cfg)
    else:
        zip_path = root / cfg.output_dir / f"local_code_change_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    files: set[Path] = set()
    for rel in include_files:
        p = root / rel
        ensure_safe_path(p, cfg)
        if p.exists() and p.is_file():
            files.add(p)
    for pattern in include_patterns:
        for p in root.glob(pattern):
            if p.is_file():
                ensure_safe_path(p, cfg)
                files.add(p)

    # Always include generated markdown reports in output_dir if present.
    reports_dir = root / cfg.output_dir
    if reports_dir.exists():
        for p in reports_dir.glob("*.md"):
            if p.is_file():
                files.add(p)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(files):
            arcname = relative_display(p, root)
            zf.write(p, arcname)
    return {"status": "success", "zip_path": str(zip_path), "file_count": len(files), "size": zip_path.stat().st_size}


def create_full_snapshot_zip(project_path: str, output_zip: str | None = None, config_path: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path)
    root = ensure_safe_project_root(project_path, cfg)
    zip_path = ensure_safe_path(output_zip, cfg) if output_zip else root / cfg.output_dir / f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for current, dirs, files in os.walk(root):
            current_path = Path(current)
            dirs[:] = [d for d in dirs if d not in set(cfg.ignored_dirs)]
            for name in files:
                p = current_path / name
                if p == zip_path:
                    continue
                try:
                    ensure_safe_path(p, cfg)
                except Exception:
                    continue
                zf.write(p, relative_display(p, root))
                count += 1
    return {"status": "success", "zip_path": str(zip_path), "file_count": count, "size": zip_path.stat().st_size}
