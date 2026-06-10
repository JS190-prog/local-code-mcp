from __future__ import annotations

import json
from typing import Any

from .command_tools import run_command_safely, run_compile_check, run_pytest
from .config import load_config, write_example_config
from .filesystem_tools import get_file_info, list_project_files, read_file, search_files, search_text, write_file_safe
from .git_tools import (
    git_add,
    git_changed_files,
    git_commit,
    git_commit_files,
    git_create_branch,
    git_diagnose,
    git_diff,
    git_restore_file,
    git_status,
)
from .package_tools import create_change_zip, create_full_snapshot_zip, generate_changelog_md
from .patch_tools import replace_in_file, restore_from_backup
from .project_tools import detect_project_type, summarize_project

try:
    from mcp.server.fastmcp import FastMCP
except Exception as exc:  # pragma: no cover - only used when optional dependency is absent
    FastMCP = None  # type: ignore[assignment]
    MCP_IMPORT_ERROR = exc
else:
    MCP_IMPORT_ERROR = None


def create_mcp_server() -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "mcp package is not installed. Install with: pip install 'local-code-mcp[mcp]' or pip install mcp"
        ) from MCP_IMPORT_ERROR

    mcp = FastMCP("local-code-mcp")

    @mcp.tool()
    def list_allowed_roots(config_path: str | None = None) -> dict[str, Any]:
        """Return the configured project roots that this MCP server may access."""
        cfg = load_config(config_path)
        return {"status": "success", "allowed_roots": cfg.allowed_roots, "output_dir": cfg.output_dir, "backup_dir": cfg.backup_dir}

    @mcp.tool()
    def create_example_config(path: str = "config.json") -> dict[str, Any]:
        """Create an example config.json file that allows C:/hwpmcp and C:/OfficeMCP."""
        out = write_example_config(path)
        return {"status": "success", "path": str(out)}

    @mcp.tool()
    def mcp_list_project_files(project_path: str, max_depth: int = 4, include_hidden: bool = False, config_path: str | None = None) -> dict[str, Any]:
        """List files inside an allowed project root."""
        return list_project_files(project_path, max_depth=max_depth, include_hidden=include_hidden, config_path=config_path)

    @mcp.tool()
    def mcp_read_file(path: str, config_path: str | None = None) -> dict[str, Any]:
        """Read a text file inside an allowed project root."""
        return read_file(path, config_path=config_path)

    @mcp.tool()
    def mcp_write_file_safe(
        path: str,
        text: str | None = None,
        content: str | None = None,
        body: str | None = None,
        encoding: str = "utf-8",
        project_root: str | None = None,
        config_path: str | None = None,
    ) -> dict[str, Any]:
        """Write a text file after creating a backup when the file already exists.

        File content may be provided with text, content, or body.
        The aliases make this tool compatible with common file-writing schemas
        while preserving the existing text parameter.
        """
        resolved_text = text if text is not None else content if content is not None else body
        if resolved_text is None:
            return {
                "status": "error",
                "error_code": "missing_file_text",
                "message": "File content is missing. Provide one of: text, content, or body.",
                "recoverable": True,
                "suggestion": "Example: {\"path\": \"C:/path/file.md\", \"text\": \"file content\"}",
            }
        return write_file_safe(path, text=resolved_text, encoding=encoding, project_root=project_root, config_path=config_path)

    @mcp.tool()
    def mcp_search_files(project_path: str, pattern: str, max_results: int = 100, config_path: str | None = None) -> dict[str, Any]:
        """Search file and directory paths by regex inside an allowed project root."""
        return search_files(project_path, pattern=pattern, max_results=max_results, config_path=config_path)

    @mcp.tool()
    def mcp_search_text(project_path: str, query: str, max_results: int = 100, config_path: str | None = None) -> dict[str, Any]:
        """Search text in readable source files inside an allowed project root."""
        return search_text(project_path, query=query, max_results=max_results, config_path=config_path)

    @mcp.tool()
    def mcp_get_file_info(path: str, config_path: str | None = None) -> dict[str, Any]:
        """Return size, type, and metadata for a path inside an allowed root."""
        return get_file_info(path, config_path=config_path)

    @mcp.tool()
    def mcp_replace_in_file(path: str, replacements_json: str, dry_run: bool = True, project_root: str | None = None, config_path: str | None = None) -> dict[str, Any]:
        """Replace exact text snippets in a file. replacements_json is a JSON list with old/new/replace_all."""
        replacements = json.loads(replacements_json)
        return replace_in_file(path, replacements=replacements, dry_run=dry_run, project_root=project_root, config_path=config_path)

    @mcp.tool()
    def mcp_restore_from_backup(backup_path: str, original_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Restore a file from a backup created by this program."""
        return restore_from_backup(backup_path, original_path, config_path=config_path)

    @mcp.tool()
    def mcp_run_command_safely(command: str, cwd: str, timeout: int = 120, config_path: str | None = None) -> dict[str, Any]:
        """Run a command only if it matches the configured allowlist and project root policy."""
        return run_command_safely(command, cwd=cwd, timeout=timeout, config_path=config_path)

    @mcp.tool()
    def mcp_run_compile_check(project_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Run python -m compileall . in an allowed project root."""
        return run_compile_check(project_path, config_path=config_path)

    @mcp.tool()
    def mcp_run_pytest(project_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Run python -m pytest in an allowed project root."""
        return run_pytest(project_path, config_path=config_path)

    @mcp.tool()
    def mcp_git_status(project_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Run git status --short in an allowed project root."""
        return git_status(project_path, config_path=config_path)

    @mcp.tool()
    def mcp_git_diagnose(project_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Diagnose Git execution from inside the MCP server process."""
        return git_diagnose(project_path, config_path=config_path)

    @mcp.tool()
    def mcp_git_diff(project_path: str, staged: bool = False, config_path: str | None = None) -> dict[str, Any]:
        """Run git diff or git diff --staged in an allowed project root."""
        return git_diff(project_path, staged=staged, config_path=config_path)

    @mcp.tool()
    def mcp_git_changed_files(project_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Return changed files from git status --porcelain."""
        return git_changed_files(project_path, config_path=config_path)

    @mcp.tool()
    def mcp_git_add(project_path: str, files_json: str, config_path: str | None = None) -> dict[str, Any]:
        """Stage selected relative file paths with git add."""
        files = json.loads(files_json)
        return git_add(project_path, files=files, config_path=config_path)

    @mcp.tool()
    def mcp_git_commit(project_path: str, message: str, config_path: str | None = None) -> dict[str, Any]:
        """Create a git commit from already staged changes."""
        return git_commit(project_path, message=message, config_path=config_path)

    @mcp.tool()
    def mcp_git_commit_files(project_path: str, files_json: str, message: str, config_path: str | None = None) -> dict[str, Any]:
        """Stage selected relative file paths and create one git commit."""
        files = json.loads(files_json)
        return git_commit_files(project_path, files=files, message=message, config_path=config_path)

    @mcp.tool()
    def mcp_git_create_branch(project_path: str, branch_name: str, config_path: str | None = None) -> dict[str, Any]:
        """Create a safety branch. Branch name must start with ai-change/."""
        return git_create_branch(project_path, branch_name=branch_name, config_path=config_path)

    @mcp.tool()
    def mcp_git_restore_file(project_path: str, rel_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Restore a changed file with git restore -- <file>."""
        return git_restore_file(project_path, rel_path=rel_path, config_path=config_path)

    @mcp.tool()
    def mcp_detect_project_type(project_path: str, config_path: str | None = None) -> dict[str, Any]:
        """Detect Python, Node, .NET, PowerShell, or MCP-like project markers."""
        return detect_project_type(project_path, config_path=config_path)

    @mcp.tool()
    def mcp_summarize_project(project_path: str, max_depth: int = 3, config_path: str | None = None) -> dict[str, Any]:
        """Summarize project type, file counts, extensions, and total scanned size."""
        return summarize_project(project_path, max_depth=max_depth, config_path=config_path)

    @mcp.tool()
    def mcp_generate_changelog_md(
        project_path: str,
        output_path: str | None = None,
        title: str = "Local Code MCP 변경사항 보고서",
        request_summary: str = "코드 수정 및 검증",
        changed_files_json: str = "[]",
        change_summary: str = "- 수정 내용을 확인한 뒤 필요한 내용을 보완하세요.",
        test_results_json: str = "[]",
        notes: str = "- 자동 생성 문서입니다. 실제 배포 전 수동 검토를 권장합니다.",
        config_path: str | None = None,
    ) -> dict[str, Any]:
        """Generate a Korean markdown changelog/report inside an allowed project root."""
        return generate_changelog_md(
            project_path=project_path,
            output_path=output_path,
            title=title,
            request_summary=request_summary,
            changed_files=changed_files_json,
            change_summary=change_summary,
            test_results=test_results_json,
            notes=notes,
            config_path=config_path,
        )

    @mcp.tool()
    def mcp_create_change_zip(
        project_path: str,
        output_zip: str | None = None,
        include_files_json: str = "[]",
        include_patterns_json: str = "[]",
        config_path: str | None = None,
    ) -> dict[str, Any]:
        """Create a ZIP containing selected changed files and generated markdown reports."""
        return create_change_zip(
            project_path=project_path,
            output_zip=output_zip,
            include_files=include_files_json,
            include_patterns=include_patterns_json,
            config_path=config_path,
        )

    @mcp.tool()
    def mcp_create_full_snapshot_zip(project_path: str, output_zip: str | None = None, config_path: str | None = None) -> dict[str, Any]:
        """Create a full snapshot ZIP, excluding ignored directories."""
        return create_full_snapshot_zip(project_path, output_zip=output_zip, config_path=config_path)

    return mcp


def main() -> None:
    server = create_mcp_server()
    server.run()


if __name__ == "__main__":
    main()
