# Local Code MCP package consolidation

## Canonical layout

Use the root project as the single source of truth:

```text
C:/local-code-mcp
├─ pyproject.toml
├─ local_code_mcp/
│  ├─ server.py
│  ├─ cli.py
│  ├─ git_tools.py
│  └─ ...
└─ tests/
```

## Deprecated nested layout

The nested project under `C:/local-code-mcp/local_code_mcp` is deprecated. It previously duplicated the whole project and could cause the MCP runtime to load a different copy of the package than the files being edited.

The nested entrypoints now delegate to the canonical root package through:

```text
C:/local-code-mcp/local_code_mcp/local_code_mcp/_canonical.py
C:/local-code-mcp/local_code_mcp/local_code_mcp/server.py
C:/local-code-mcp/local_code_mcp/local_code_mcp/cli.py
```

## Required operational step

Restart or reinstall localcodemcp from the canonical root:

```bat
cd /d C:\local-code-mcp
pip install -e .
```

Then restart the MCP server and confirm these tools appear:

```text
mcp_git_add
mcp_git_commit
mcp_git_commit_files
```

## Manual cleanup after verification

After confirming no launcher uses the nested path, remove the deprecated duplicate project:

```text
C:/local-code-mcp/local_code_mcp/pyproject.toml
C:/local-code-mcp/local_code_mcp/tests
C:/local-code-mcp/local_code_mcp/local_code_mcp
C:/local-code-mcp/local_code_mcp/README_DEPRECATED_NESTED_PROJECT.md
```

The current MCP toolset does not expose a delete operation, so deletion must be performed manually after verification.
