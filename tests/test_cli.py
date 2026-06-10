import json
import subprocess
import sys


def _run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "local_code_mcp.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_cli_run_blocks_disallowed_command_with_json_error(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"allowed_roots": [str(project)]}), encoding="utf-8")

    proc = _run_cli(["--config", str(config), "run", str(project), "rm -rf ."], cwd=".")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["status"] == "error"
    assert data["error_type"] == "SafetyError"
    assert "blocked" in data["message"].lower()


def test_cli_read_outside_allowed_root_returns_json_error(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"allowed_roots": [str(project)]}), encoding="utf-8")

    proc = _run_cli(["--config", str(config), "read", str(outside)], cwd=".")
    assert proc.returncode == 1
    data = json.loads(proc.stdout)
    assert data["status"] == "error"
    assert data["error_type"] == "SafetyError"
    assert "outside allowed roots" in data["message"].lower()
