from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_NAME = "config.json"


@dataclass
class LocalCodeConfig:
    """Runtime configuration for Local Code MCP."""

    allowed_roots: list[str] = field(default_factory=list)
    blocked_globs: list[str] = field(default_factory=lambda: [
        "**/.env",
        "**/.env.*",
        "**/*id_rsa*",
        "**/*.pem",
        "**/*.key",
        "**/AppData/**",
        "C:/Windows/**",
        "C:/Program Files/**",
        "C:/Program Files (x86)/**",
    ])
    ignored_dirs: list[str] = field(default_factory=lambda: [
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "dist",
        "build",
    ])
    allowed_commands: list[str] = field(default_factory=lambda: [
        "python -m compileall",
        "python -m pytest",
        "pytest",
        "npm test",
        "npm run lint",
        "git status",
        "git diff",
        "git log",
        "pip install -r requirements.txt",
    ])
    blocked_command_fragments: list[str] = field(default_factory=lambda: [
        "del /s",
        "rmdir /s",
        "format ",
        "shutdown",
        "reg delete",
        "rm -rf",
        "curl ",
        "wget ",
        "invoke-webrequest",
        "iwr ",
        "start-process powershell",
        "powershell -enc",
        "certutil ",
    ])
    backup_dir: str = "local_artifacts/backups"
    output_dir: str = "local_artifacts/changes"
    max_file_bytes: int = 2_000_000
    default_encoding: str = "utf-8"
    git_executable: str = "git"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LocalCodeConfig":
        base = cls()
        for key, value in data.items():
            if hasattr(base, key):
                setattr(base, key, value)
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_roots": self.allowed_roots,
            "blocked_globs": self.blocked_globs,
            "ignored_dirs": self.ignored_dirs,
            "allowed_commands": self.allowed_commands,
            "blocked_command_fragments": self.blocked_command_fragments,
            "backup_dir": self.backup_dir,
            "output_dir": self.output_dir,
            "max_file_bytes": self.max_file_bytes,
            "default_encoding": self.default_encoding,
            "git_executable": self.git_executable,
        }


def default_config_path() -> Path:
    env_path = os.environ.get("LOCAL_CODE_MCP_CONFIG")
    if env_path:
        return Path(env_path)
    return Path.cwd() / DEFAULT_CONFIG_NAME


def load_config(config_path: str | Path | None = None) -> LocalCodeConfig:
    path = Path(config_path) if config_path else default_config_path()
    if not path.exists():
        return LocalCodeConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return LocalCodeConfig.from_dict(data)


def write_example_config(path: str | Path) -> Path:
    path = Path(path)
    cfg = LocalCodeConfig(
        allowed_roots=[
            "C:/hwpmcp",
            "C:/OfficeMCP",
        ]
    )
    path.write_text(json.dumps(cfg.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
