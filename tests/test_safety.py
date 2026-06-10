import json
from pathlib import Path

import pytest

from local_code_mcp.config import LocalCodeConfig
from local_code_mcp.safety import SafetyError, ensure_command_allowed, ensure_safe_path


def test_safe_path_allows_tmp_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    cfg = LocalCodeConfig(allowed_roots=[str(project)])
    assert ensure_safe_path(project / "a.txt", cfg) == (project / "a.txt").resolve(strict=False)


def test_safe_path_blocks_outside(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.txt"
    cfg = LocalCodeConfig(allowed_roots=[str(project)])
    with pytest.raises(SafetyError):
        ensure_safe_path(outside, cfg)


def test_command_allowlist():
    cfg = LocalCodeConfig(allowed_roots=["C:/x"])
    ensure_command_allowed("python -m compileall .", cfg)
    with pytest.raises(SafetyError):
        ensure_command_allowed("del /s C:\\x", cfg)
