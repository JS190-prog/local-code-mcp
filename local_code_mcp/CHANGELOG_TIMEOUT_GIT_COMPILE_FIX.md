# Local Code MCP 실패/제한 원인 수정 보고서

## 1. 작업 개요
- 대상 프로그램: Local Code MCP
- 수정 목적: `git status` 및 `python -m compileall .` 실행 시 MCP 호출이 타임아웃으로 실패하던 문제 개선
- 수정 결과: Git 비저장소는 즉시 `skipped`로 반환하고, 컴파일 검사는 생성물/백업 폴더를 제외한 Python 소스만 검사하도록 변경

## 2. 확인된 원인

### 2.1 Git 상태 조회 타임아웃
기존 `git_status()`는 대상 폴더가 Git 저장소인지 사전 확인하지 않고 바로 `git status --short`를 실행했습니다.
Windows 환경에서 Git이 상위 경로를 탐색하거나 잠금/대형 작업트리/비저장소 상태를 처리하는 동안 응답이 늦어지면 MCP 도구 호출 자체가 `TimeoutError`로 끝났습니다.

### 2.2 컴파일 검사 타임아웃
기존 `run_compile_check()`는 `python -m compileall .`을 프로젝트 루트 전체에 대해 실행했습니다.
로컬 작업 폴더에 `local_artifacts`, 백업, 로그, 샘플 문서, 캐시가 많아지면 실제 소스가 아닌 폴더까지 재귀 탐색하면서 검증 시간이 길어질 수 있었습니다.

### 2.3 타임아웃 응답 비표준
기존 `run_command_safely()`와 Git 실행 함수는 `subprocess.TimeoutExpired`를 구조화된 JSON으로 변환하지 않아, 호출자 입장에서는 원인을 구분하기 어려운 일반 `TimeoutError`로 보였습니다.

## 3. 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `local_code_mcp/command_tools.py` | 명령 실행 타임아웃을 JSON 응답으로 반환, 컴파일 검사를 `py_compile` 기반 선택 소스 검사로 변경 |
| `local_code_mcp/git_tools.py` | `.git` 사전 확인, 비저장소 즉시 `skipped` 반환, Git 명령 timeout 처리, untracked 스캔 축소 |
| `tests/test_command_tools.py` | 명령 타임아웃 JSON 응답 및 컴파일 검사 제외 폴더 테스트 추가 |
| `tests/test_git_tools.py` | 비Git 프로젝트에서 즉시 `skipped` 반환 테스트 추가 |

## 4. 주요 변경 내용

### 4.1 명령 실행 타임아웃 구조화
`run_command_safely()`가 제한 시간을 초과하면 예외를 그대로 노출하지 않고 다음 형식으로 반환합니다.

```json
{
  "status": "timeout",
  "error_code": "command_timeout",
  "timeout_seconds": 120,
  "suggestion": "명령이 제한 시간 안에 끝나지 않았습니다..."
}
```

### 4.2 컴파일 검사 개선
기존:

```text
python -m compileall .
```

변경:

```text
py_compile 기반으로 .py 파일만 선별 검사
local_artifacts, artifacts, backups, logs, hwp_samples, .git, .venv, __pycache__ 등 제외
```

### 4.3 Git 상태 조회 개선
Git 명령 실행 전 `.git` 디렉터리 또는 `.git` 파일이 있는지 먼저 확인합니다.
없으면 Git을 실행하지 않고 즉시 반환합니다.

```json
{
  "status": "skipped",
  "error_code": "not_git_repository"
}
```

Git 저장소인 경우에도 다음 옵션을 적용했습니다.

```text
--untracked-files=no
--no-ext-diff
--no-color
GIT_TERMINAL_PROMPT=0
GIT_PAGER=cat
```

## 5. 검증 결과

| 검증 항목 | 결과 |
|---|---:|
| Python 문법 검사 | 통과 |
| 단위 테스트 | 통과 |
| 명령 타임아웃 JSON 반환 테스트 | 통과 |
| 컴파일 검사 제외 폴더 테스트 | 통과 |
| 비Git 프로젝트 즉시 skipped 반환 테스트 | 통과 |

테스트 명령:

```bash
python -m compileall local_code_mcp tests
python -m pytest -q
```

결과:

```text
10 passed
```

## 6. 적용 방법

1. 기존 Local Code MCP 폴더를 백업합니다.
2. 이 ZIP의 `local_code_mcp/` 패키지 파일을 기존 설치 폴더에 덮어씁니다.
3. MCP 서버를 재시작합니다.
4. 다시 `mcp_git_status`, `mcp_run_compile_check`를 실행합니다.

## 7. 주의사항

- 현재 실행 중인 LocalCodeMCP 서버는 재시작 전까지 수정 코드가 반영되지 않습니다.
- `C:/hwpmcp`가 Git 저장소가 아니라면 Git 상태 조회는 실패가 아니라 `skipped/not_git_repository`로 표시됩니다.
- 전체 프로젝트 명령 실행은 여전히 환경에 따라 오래 걸릴 수 있으므로 장시간 테스트는 timeout 값을 늘리거나 테스트 범위를 줄이는 것이 좋습니다.
