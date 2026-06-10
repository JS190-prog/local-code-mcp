# Windows 설치 가이드

## 1. 압축 해제

예시:

```powershell
Expand-Archive .\local_code_mcp.zip C:\local-code-mcp
cd C:\local-code-mcp\local_code_mcp
```

압축 구조에 따라 실제 폴더명은 다를 수 있습니다.

## 2. 가상환경 생성

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
pip install "mcp>=1.0.0"
```

## 3. 설정 파일 생성

```powershell
local-code-mcp init-config config.json
```

`config.json`의 `allowed_roots`를 실제 폴더에 맞게 수정하세요.

```json
{
  "allowed_roots": [
    "C:/hwpmcp",
    "C:/OfficeMCP"
  ]
}
```

## 4. CLI 동작 확인

```powershell
local-code-mcp --config config.json list C:/hwpmcp --max-depth 2
```

## 5. MCP 서버 실행

```powershell
$env:LOCAL_CODE_MCP_CONFIG="C:\local-code-mcp\config.json"
python -m local_code_mcp.server
```

## 6. MCP 클라이언트 연결 예시

```json
{
  "mcpServers": {
    "local-code-mcp": {
      "command": "C:/local-code-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "local_code_mcp.server"],
      "env": {
        "LOCAL_CODE_MCP_CONFIG": "C:/local-code-mcp/config.json"
      }
    }
  }
}
```
