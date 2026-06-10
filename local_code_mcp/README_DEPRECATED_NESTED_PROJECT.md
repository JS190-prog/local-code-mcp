# Deprecated nested Local Code MCP project

This nested project folder is kept only for backward compatibility with older launch configurations.

Canonical project root:

```text
C:/local-code-mcp
```

Canonical package:

```text
C:/local-code-mcp/local_code_mcp
```

Do not edit files under this nested project as the source of truth. Update the canonical root package instead.

Recommended launch/install path:

```bat
cd /d C:\local-code-mcp
pip install -e .
```

After reinstalling or restarting the MCP server from the canonical root, this nested project folder can be removed manually after confirming no launcher uses it.
