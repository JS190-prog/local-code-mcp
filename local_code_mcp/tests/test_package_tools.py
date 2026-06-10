import json
import zipfile

from local_code_mcp.package_tools import create_change_zip, generate_changelog_md


def test_changelog_and_zip(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "a.py").write_text("print('ok')\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"allowed_roots": [str(project)]}), encoding="utf-8")

    changelog = generate_changelog_md(str(project), changed_files=["a.py"], config_path=str(config))
    assert changelog["status"] == "success"
    assert "변경사항" in changelog["content"]

    result = create_change_zip(str(project), include_files=["a.py"], config_path=str(config))
    assert result["status"] == "success"
    with zipfile.ZipFile(result["zip_path"]) as zf:
        names = zf.namelist()
    assert "a.py" in names
    assert any(name.endswith(".md") for name in names)
