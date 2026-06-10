param(
    [string]$InstallPath = "C:\local-code-mcp"
)

Write-Host "Installing Local Code MCP to $InstallPath"

if (!(Test-Path $InstallPath)) {
    New-Item -ItemType Directory -Path $InstallPath | Out-Null
}

Set-Location $InstallPath
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install "mcp>=1.0.0"

if (!(Test-Path "config.json")) {
    local-code-mcp init-config config.json
}

Write-Host "Done. Edit config.json and run:"
Write-Host '$env:LOCAL_CODE_MCP_CONFIG="C:\local-code-mcp\config.json"'
Write-Host "python -m local_code_mcp.server"
