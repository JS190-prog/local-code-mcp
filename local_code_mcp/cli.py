from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .command_tools import run_command_safely, run_compile_check, run_pytest
from .config import write_example_config
from .filesystem_tools import list_project_files, read_file, search_files, search_text
from .git_tools import git_changed_files, git_diff, git_status
from .package_tools import create_change_zip, generate_changelog_md
from .patch_tools import replace_in_file
from .project_tools import summarize_project
from .safety import SafetyError


def _print(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _error(exc: BaseException) -> None:
    _print({
        "status": "error",
        "error_type": type(exc).__name__,
        "message": str(exc),
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="local-code-mcp", description="Safe local project editing MCP helper")
    parser.add_argument("--config", default=None, help="Path to config.json")
    sub = parser.add_subparsers(dest="action", required=True)

    p = sub.add_parser("init-config", help="Create example config.json")
    p.add_argument("path", nargs="?", default="config.json")

    p = sub.add_parser("list", help="List project files")
    p.add_argument("project_path")
    p.add_argument("--max-depth", type=int, default=4)
    p.add_argument("--include-hidden", action="store_true")

    p = sub.add_parser("read", help="Read a file")
    p.add_argument("path")

    p = sub.add_parser("search-files", help="Search file paths by regex")
    p.add_argument("project_path")
    p.add_argument("pattern")

    p = sub.add_parser("search-text", help="Search text in project")
    p.add_argument("project_path")
    p.add_argument("query")

    p = sub.add_parser("replace", help="Replace exact text in file")
    p.add_argument("path")
    p.add_argument("--old", required=True)
    p.add_argument("--new", required=True)
    p.add_argument("--replace-all", action="store_true")
    p.add_argument("--apply", action="store_true", help="Apply change. Default is dry-run.")
    p.add_argument("--project-root", default=None)

    p = sub.add_parser("run", help="Run allowlisted command")
    p.add_argument("cwd")
    p.add_argument("command_text")
    p.add_argument("--timeout", type=int, default=120)

    p = sub.add_parser("compile", help="Run python compile check")
    p.add_argument("project_path")

    p = sub.add_parser("pytest", help="Run pytest")
    p.add_argument("project_path")

    p = sub.add_parser("git-status", help="Git status")
    p.add_argument("project_path")

    p = sub.add_parser("git-diff", help="Git diff")
    p.add_argument("project_path")
    p.add_argument("--staged", action="store_true")

    p = sub.add_parser("changed-files", help="Git changed files")
    p.add_argument("project_path")

    p = sub.add_parser("summary", help="Summarize project")
    p.add_argument("project_path")

    p = sub.add_parser("changelog", help="Generate changelog md")
    p.add_argument("project_path")
    p.add_argument("--output", default=None)
    p.add_argument("--request-summary", default="코드 수정 및 검증")
    p.add_argument("--changed-files-json", default="[]")
    p.add_argument("--change-summary", default="- 수정 내용을 확인한 뒤 필요한 내용을 보완하세요.")

    p = sub.add_parser("zip", help="Create changed files zip")
    p.add_argument("project_path")
    p.add_argument("--output", default=None)
    p.add_argument("--include-files-json", default="[]")
    p.add_argument("--include-patterns-json", default="[]")
    return parser


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "init-config":
        return {"status": "success", "path": str(write_example_config(args.path))}
    if args.action == "list":
        return list_project_files(args.project_path, max_depth=args.max_depth, include_hidden=args.include_hidden, config_path=args.config)
    if args.action == "read":
        return read_file(args.path, config_path=args.config)
    if args.action == "search-files":
        return search_files(args.project_path, args.pattern, config_path=args.config)
    if args.action == "search-text":
        return search_text(args.project_path, args.query, config_path=args.config)
    if args.action == "replace":
        repl = [{"old": args.old, "new": args.new, "replace_all": args.replace_all}]
        return replace_in_file(args.path, replacements=repl, dry_run=not args.apply, project_root=args.project_root, config_path=args.config)
    if args.action == "run":
        return run_command_safely(args.command_text, cwd=args.cwd, timeout=args.timeout, config_path=args.config)
    if args.action == "compile":
        return run_compile_check(args.project_path, config_path=args.config)
    if args.action == "pytest":
        return run_pytest(args.project_path, config_path=args.config)
    if args.action == "git-status":
        return git_status(args.project_path, config_path=args.config)
    if args.action == "git-diff":
        return git_diff(args.project_path, staged=args.staged, config_path=args.config)
    if args.action == "changed-files":
        return git_changed_files(args.project_path, config_path=args.config)
    if args.action == "summary":
        return summarize_project(args.project_path, config_path=args.config)
    if args.action == "changelog":
        return generate_changelog_md(
            args.project_path,
            output_path=args.output,
            request_summary=args.request_summary,
            changed_files=args.changed_files_json,
            change_summary=args.change_summary,
            config_path=args.config,
        )
    if args.action == "zip":
        return create_change_zip(
            args.project_path,
            output_zip=args.output,
            include_files=args.include_files_json,
            include_patterns=args.include_patterns_json,
            config_path=args.config,
        )
    raise ValueError(f"Unsupported command: {args.action}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _print(dispatch(args))
    except (SafetyError, FileNotFoundError, IsADirectoryError, PermissionError, ValueError, json.JSONDecodeError) as exc:
        _error(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
