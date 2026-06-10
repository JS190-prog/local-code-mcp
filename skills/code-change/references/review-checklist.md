# 코드 변경 검토 체크리스트

## Archive intake

- Keep the original archive untouched.
- Extract into a new working directory.
- Identify whether the archive contains a single project root or multiple nested projects.
- Search for README, pyproject, package.json, requirements, setup scripts, MCP config files, and tests.

## Patch discipline

- Modify the fewest files necessary.
- Preserve existing public function names and tool schemas when possible.
- Add optional parameters instead of changing defaults.
- Keep generated output filenames English-only.

## Validation ladder

Use the strongest available validation, in this order:

1. Existing test suite.
2. Targeted smoke test for the modified feature.
3. Syntax check or compile check.
4. Static inspection with grep/diff.
5. Manual limitation note when none of the above can run.

## Delivery package

Default zip contents:

- `CHANGELOG_*.md` at root.
- `MANIFEST_CODE_CHANGE.json` at root.
- Changed code files under `modified_code/<original-relative-path>`.

Do not include caches, virtual environments, build artifacts, secrets, credentials, or the full unmodified repository unless the user explicitly asks.
