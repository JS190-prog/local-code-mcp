import json

from local_code_mcp.git_tools import git_status


def test_git_status_skips_non_git_project_without_invoking_git(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"allowed_roots": [str(project)]}), encoding="utf-8")

    result = git_status(str(project), config_path=str(config))
    assert result["status"] == "skipped"
    assert result["error_code"] == "not_git_repository"
