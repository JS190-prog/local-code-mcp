---
name: code-change
description: modify uploaded code archives or project folders and return a safe deliverable zip containing only changed code files plus a markdown changelog. use when the user asks to patch a program, fix a bug, update paths, improve an mcp connector such as hwpmcp or officemcp, add background or focus behavior, or create a modified-code package from a zip. the skill emphasizes inspection, minimal reversible changes, validation, and transparent reporting of what was changed and what could not be verified.
---

# 코드변경

## Purpose

Use this skill to modify code in an uploaded archive or project folder, validate the change as far as the environment allows, and deliver a compact zip containing the changed code plus a markdown changelog.

The user-facing display name is **코드변경**. The internal skill identifier is `code-change` because skill package identifiers must use lowercase ASCII hyphen-case.

## Core Workflow

1. **Inspect before editing**
   - Unpack the archive into a working directory.
   - List the top-level structure and identify languages, entrypoints, configuration files, tests, and likely target files.
   - Never assume a file exists; verify paths before editing.
   - Preserve the original archive and keep a separate working copy.

2. **Clarify only when the requested change is underspecified**
   - Proceed without additional questions when the request and prior conversation provide enough intent.
   - Ask a focused question only if applying the change would require guessing business logic, credentials, production paths, or destructive behavior.

3. **Make minimal, compatible changes**
   - Prefer small targeted patches over rewrites.
   - Preserve public APIs unless the user explicitly asks for breaking changes.
   - For existing behavior, keep defaults backward compatible.
   - Add defensive checks and clearer errors around the exact failure mode.

4. **Validate**
   - Run available unit tests, linters, syntax checks, or targeted smoke tests.
   - If dependencies are unavailable, run lightweight checks such as `python -m py_compile`, JSON/YAML parsing, import checks, or static grep review.
   - Be explicit about validations that could not be run.

5. **Create the deliverable**
   - Include only changed code files and the changelog unless the user asks for a full project archive.
   - Use English filenames for generated artifacts.
   - Put the changelog at the zip root.
   - Use `scripts/make_change_package.py` when practical.

6. **Final response**
   - Link to the zip and changelog.
   - Summarize changed files, validation performed, and known limitations.
   - Do not claim a runtime integration works unless it was actually tested.

## Required Changelog Format

Create a markdown file named like `CHANGELOG_<PROJECT>_<CHANGE>.md` with this structure:

```markdown
# <Project> change log

## Summary
<One paragraph describing the purpose of the change.>

## Changed files
| File | Change |
|---|---|
| path/to/file.py | Added ... |

## Behavior changes
- Before: ...
- After: ...

## Validation
| Check | Result |
|---|---|
| python -m py_compile ... | Passed |

## Limitations / manual follow-up
- <State anything not verified.>

## Apply instructions
1. Back up the current project folder.
2. Copy the changed files into the matching paths.
3. Restart the affected service or MCP server.
4. Run the validation command(s) above.
```

## Packaging Helper

Use the helper script when producing the final zip:

```bash
python /home/oai/skills/code-change/scripts/make_change_package.py \
  --repo /path/to/workdir \
  --output /mnt/data/project_change_fix.zip \
  --changelog /path/to/CHANGELOG_PROJECT_FIX.md \
  --changed-files src/file1.py src/file2.py
```

The helper packages changed code under `modified_code/`, puts the changelog at the zip root, and writes `MANIFEST_CODE_CHANGE.json`.

## MCP Connector Change Guidance

When modifying MCP programs such as `hwpmcp` or `officemcp`:

- Keep tool names and argument defaults compatible unless the user explicitly requests a migration.
- Add new options as optional parameters, for example `background`, `visible`, `activate_window`, or `restore_focus`.
- Preserve user focus where possible:
  - Record the current foreground window before automation.
  - Avoid `SetForegroundWindow`, `SendKeys`, or mouse/keyboard simulation unless unavoidable.
  - Restore the previous foreground window in a `finally` block.
- Add a diagnostic tool or structured status response when feasible.
- Standardize errors as `{status, stage, error_code, message, recoverable, suggestion}` when changing existing error handling.

### HWP / hwpmcp specific safeguards

For HWP automation, prioritize document safety:

- Treat focus-stealing as a bug unless the user explicitly asks for interactive control.
- Prefer COM/document object methods over foreground-window control.
- For table creation, verify actual table count before and after insertion.
- Never return `status: success` when `table_created` is false.
- If table creation fails, do not insert table data as plain text fallback unless the user explicitly requested fallback text.
- For fill-table tools, ensure the HWP object is initialized in the same scope where it is used; avoid errors like `name 'hwp' is not defined`.
- For destructive or large operations, provide rollback behavior or clear manual rollback instructions.


## Local MCP Tooling Safeguards

When changing local MCP connector code or local-code-mcp itself:

- Treat the running MCP server process as stale after editing files. State that the affected MCP server must be restarted before runtime retesting, unless the server was demonstrably restarted during the task.
- Distinguish file-level validation from runtime-tool validation. A syntax check on changed files does not prove the already-running MCP tool is using the new code.
- Do not rely on a tool's `status: success` alone. Cross-check observable state with a second tool when available, for example table counts, file existence, generated zip contents, git status, or read-only status tools.
- If a packaging tool fails or is blocked, make one safer narrower attempt. If that also fails, report the failure and provide the created changelog and changed-file paths instead of claiming a complete package.
- For local-code-mcp specifically, prefer project virtualenv Python for pytest, avoid scanning virtualenv/artifact directories for syntax checks, and return structured timeout/missing-dependency results rather than raw exceptions.
- For Git helpers, guard against non-repositories, timeouts, missing Git, and empty outputs; return structured JSON instead of allowing exceptions to escape.
- For generated changelogs, preserve test result fields named `check`, `name`, `command`, `result`, `status`, `detail`, `message`, `stdout`, `stderr`, or `returncode` so validation tables do not degrade to `unknown`.

## Review Checklist

Before packaging, check:

- [ ] The zip was unpacked and inspected.
- [ ] Changed files are limited to the requested behavior.
- [ ] The changelog states all changed files.
- [ ] Tests or static checks were run.
- [ ] Generated artifact filenames are English-only.
- [ ] The output zip does not include the entire original project unless requested.
- [ ] The final response does not overstate verification.
