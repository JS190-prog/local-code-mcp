# Local Code MCP

`Local Code MCP`는 Windows 로컬 폴더의 프로그램 코드를 ChatGPT/MCP에서 안전하게 확인, 수정, 검증, 패키징하기 위한 로컬 MCP 서버입니다.

`config.json`의 `allowed_roots`에 등록한 폴더를 직접 연결해서 다음 작업을 수행합니다.

- 로컬 프로젝트 파일 목록 확인
- 코드 파일 읽기
- 파일명/본문 검색
- 안전한 텍스트 패치 및 dry-run diff 확인
- 수정 전 자동 백업
- Git status/diff 확인
- 허용된 테스트 명령 실행
- 변경사항 `.md` 생성
- 수정 파일 ZIP 생성

## 핵심 안전장치

1. `config.json`의 `allowed_roots` 안에 있는 폴더만 접근합니다.
2. `.env`, 개인키, Windows 시스템 폴더 등은 기본 차단합니다.
3. 코드 수정 전 백업을 생성합니다.
4. 기본 수정은 `dry_run`으로 diff를 먼저 확인할 수 있습니다.
5. 명령 실행은 allowlist에 등록된 명령만 허용합니다.
6. 삭제 기능은 기본 구현하지 않았습니다.

## 설치

Python 3.10 이상을 권장합니다.

```powershell
cd C:\local-code-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pip install "mcp>=1.0.0"
```

## 설정

처음에는 예시 설정 파일을 만듭니다.

```powershell
local-code-mcp init-config config.json
```

`config.json`에서 허용할 폴더를 확인합니다.

```json
{
  "allowed_roots": [
    "C:/hwpmcp",
    "C:/OfficeMCP"
  ]
}
```

## CLI 사용 예시

파일 목록:

```powershell
local-code-mcp --config config.json list C:/hwpmcp --max-depth 3
```

본문 검색:

```powershell
local-code-mcp --config config.json search-text C:/hwpmcp table_created
```

수정 전 dry-run:

```powershell
local-code-mcp --config config.json replace C:/hwpmcp/server.py --old "status: success" --new "status: error"
```

실제 적용:

```powershell
local-code-mcp --config config.json replace C:/hwpmcp/server.py --old "status: success" --new "status: error" --apply --project-root C:/hwpmcp
```

문법 검사:

```powershell
local-code-mcp --config config.json compile C:/hwpmcp
```

Git diff:

```powershell
local-code-mcp --config config.json git-diff C:/hwpmcp
```

변경사항 문서 생성:

```powershell
local-code-mcp --config config.json changelog C:/hwpmcp --request-summary "표 생성 오류 수정"
```

ZIP 생성:

```powershell
local-code-mcp --config config.json zip C:/hwpmcp --include-files-json '["server.py"]'
```

## MCP 서버 실행

```powershell
$env:LOCAL_CODE_MCP_CONFIG="C:\local-code-mcp\config.json"
python -m local_code_mcp.server
```

MCP 클라이언트에는 stdio 서버로 등록합니다. 예시:

```json
{
  "mcpServers": {
    "local-code-mcp": {
      "command": "python",
      "args": ["-m", "local_code_mcp.server"],
      "env": {
        "LOCAL_CODE_MCP_CONFIG": "C:/local-code-mcp/config.json"
      }
    }
  }
}
```

## 제공 MCP 도구

- `list_allowed_roots`
- `create_example_config`
- `mcp_list_project_files`
- `mcp_read_file`
- `mcp_write_file_safe`
- `mcp_search_files`
- `mcp_search_text`
- `mcp_get_file_info`
- `mcp_replace_in_file`
- `mcp_restore_from_backup`
- `mcp_run_command_safely`
- `mcp_run_compile_check`
- `mcp_run_pytest`
- `mcp_git_status`
- `mcp_git_diff`
- `mcp_git_changed_files`
- `mcp_git_create_branch`
- `mcp_git_restore_file`
- `mcp_detect_project_type`
- `mcp_summarize_project`
- `mcp_generate_changelog_md`
- `mcp_create_change_zip`
- `mcp_create_full_snapshot_zip`

## ChatGPT 스킬: 코드변경 (`skills/code-change`)

이 저장소에는 MCP 서버와 별도로, ChatGPT에서 바로 쓸 수 있는 Agent Skill이 `skills/code-change/`에 포함되어 있습니다.

### 용도

ChatGPT에 업로드한 코드 압축파일이나 프로젝트 폴더를 수정할 때, 아래 워크플로를 일관되게 강제하는 스킬입니다.

- 수정 전 압축 해제 및 구조 분석 (파일 존재 여부를 확인한 뒤에만 편집)
- 최소·호환 가능한 패치 위주 수정 (불필요한 리라이트 금지)
- 가능한 범위의 검증 실행 (`py_compile`, 테스트, 정적 점검) 및 미검증 항목 명시
- 변경된 코드 파일 + 마크다운 changelog만 담은 결과물 ZIP 생성
- hwpmcp / officemcp 같은 MCP 커넥터 수정 시 포커스 보존, 표 생성 검증 등 안전 규칙 적용

ChatGPT에서 표시되는 이름은 **코드변경**이며, 내부 식별자는 `code-change`입니다.

### 폴더 구조

```
skills/code-change/
├── SKILL.md                        # 스킬 본문 (워크플로, changelog 형식, 체크리스트)
├── agents/openai.yaml              # 표시 이름·아이콘·자동 호출 정책
├── scripts/make_change_package.py  # 변경 파일 + changelog ZIP 패키징 헬퍼
├── references/review-checklist.md  # 패키징 전 리뷰 체크리스트
└── assets/icon.svg
```

### ChatGPT에 추가하는 방법

1. 스킬 폴더를 ZIP으로 압축합니다.

   ```powershell
   Compress-Archive -Path C:\local-code-mcp\skills\code-change -DestinationPath C:\local-code-mcp\code-change-skill.zip
   ```

2. ChatGPT에서 프로필 아이콘 → **Skills** → **New skill** → **Upload from your computer**를 선택해 ZIP을 업로드합니다.
3. 업로드 시 자동 스캔이 진행되며, 대부분 스캔 완료 직후 바로 사용 가능합니다.
4. 설치 후에는 코드 수정 요청 시 ChatGPT가 자동으로 이 스킬을 사용합니다(`allow_implicit_invocation: true`). "코드변경 스킬로 수정해줘"처럼 명시적으로 호출할 수도 있습니다.

참고:

- 스킬 기능은 현재 베타이며 ChatGPT Business / Enterprise / Edu 등 일부 플랜에서 제공됩니다. 자세한 내용은 [Skills in ChatGPT(OpenAI Help Center)](https://help.openai.com/en/articles/20001066-skills-in-chatgpt)를 확인하세요.
- Agent Skills 개방 표준 형식이므로 같은 폴더를 그대로 Codex에서도 사용할 수 있습니다([Codex Agent Skills 문서](https://developers.openai.com/codex/skills)).

## 현재 버전의 한계

- GUI 프로그램을 직접 클릭하는 기능은 포함하지 않았습니다. 코드 수정은 파일시스템 기반으로 처리합니다.
- 통합 대상 MCP 클라이언트의 등록 방식은 환경에 따라 다를 수 있습니다.
- `mcp` Python 패키지 버전에 따라 서버 실행 방식 조정이 필요할 수 있습니다.
- 보안상 전체 C드라이브 접근은 권장하지 않습니다.

## 권장 운영 방식

1. `allowed_roots`를 필요한 프로젝트 폴더로만 제한합니다.
2. 먼저 `dry_run`으로 diff를 확인합니다.
3. 수정 전 Git 상태를 확인합니다.
4. 수정 후 `compile`, `pytest`, `git-diff`를 실행합니다.
5. 변경사항 `.md`와 ZIP을 생성합니다.
