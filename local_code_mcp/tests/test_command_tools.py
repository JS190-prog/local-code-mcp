import json

from local_code_mcp.command_tools import run_command_safely, run_compile_check


def test_run_command_safely_returns_timeout_json(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "allowed_roots": [str(project)],
        "allowed_commands": ["python"],
    }), encoding="utf-8")

    result = run_command_safely(
        "python -c \"import time; time.sleep(2)\"",
        cwd=str(project),
        timeout=1,
        config_path=str(config),
    )
    assert result["status"] == "timeout"
    assert result["error_code"] == "command_timeout"


def test_run_compile_check_skips_local_artifacts(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "ok.py").write_text("x = 1\n", encoding="utf-8")
    artifacts = project / "local_artifacts" / "changes"
    artifacts.mkdir(parents=True)
    (artifacts / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"allowed_roots": [str(project)]}), encoding="utf-8")

    result = run_compile_check(str(project), config_path=str(config))
    assert result["status"] == "success"
    assert result["files_checked"] == 1
