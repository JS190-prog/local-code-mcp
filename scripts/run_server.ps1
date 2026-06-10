$env:LOCAL_CODE_MCP_CONFIG = Join-Path $PSScriptRoot "..\config.json"
python -m local_code_mcp.server
