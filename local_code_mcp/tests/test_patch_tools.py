import json

from local_code_mcp.config import write_example_config
from local_code_mcp.patch_tools import replace_in_file


def test_replace_in_file_dry_run_and_apply(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    target = project / "a.py"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"allowed_roots": [str(project)]}), encoding="utf-8")

    dry = replace_in_file(str(target), [{"old": "beta", "new": "gamma"}], dry_run=True, project_root=str(project), config_path=str(config))
    assert dry["status"] == "dry_run"
    assert dry["changed"] is True
    assert "gamma" in dry["diff"]
    assert target.read_text(encoding="utf-8") == "alpha\nbeta\n"

    applied = replace_in_file(str(target), [{"old": "beta", "new": "gamma"}], dry_run=False, project_root=str(project), config_path=str(config))
    assert applied["status"] == "success"
    assert target.read_text(encoding="utf-8") == "alpha\ngamma\n"
    assert applied["backup"]
