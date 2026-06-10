# Local Code MCP 제작 및 수정 내용

## 1. 제작 목적

Windows 로컬 폴더의 프로그램을 ZIP 업로드 없이 직접 확인하고 수정하기 위한 MCP 서버/CLI 프로그램을 제작했습니다.

## 2. 포함 기능

| 기능 | 내용 |
|---|---|
| 허용 루트 제한 | `config.json`의 `allowed_roots` 내부만 접근 |
| 파일 목록 | 프로젝트 파일 트리 확인 |
| 파일 읽기 | UTF-8, CP949, EUC-KR 등 자동 감지 |
| 코드 검색 | 파일명 및 본문 검색 |
| 안전 수정 | dry-run diff, 백업 후 적용 |
| 명령 실행 | allowlist 명령만 실행 |
| Git 확인 | status, diff, changed files |
| 검증 | compileall, pytest 실행 도구 |
| 문서화 | 변경사항 `.md` 자동 생성 |
| 패키징 | 수정 파일과 보고서를 ZIP으로 생성 |

## 3. 주요 파일

| 파일 | 설명 |
|---|---|
| `local_code_mcp/server.py` | MCP 서버 진입점 |
| `local_code_mcp/cli.py` | CLI 진입점 |
| `local_code_mcp/config.py` | 설정 로드/예시 생성 |
| `local_code_mcp/safety.py` | 경로/명령 안전 정책 |
| `local_code_mcp/filesystem_tools.py` | 파일 목록/읽기/검색/쓰기 |
| `local_code_mcp/patch_tools.py` | dry-run 및 텍스트 패치 |
| `local_code_mcp/command_tools.py` | 안전 명령 실행 |
| `local_code_mcp/git_tools.py` | Git 상태/diff 확인 |
| `local_code_mcp/package_tools.py` | changelog 및 ZIP 생성 |
| `local_code_mcp/project_tools.py` | 프로젝트 유형 감지 |

## 4. 테스트 후 반영한 수정

| 구분 | 수정 내용 |
|---|---|
| CLI 명령 파서 | `run` 명령의 인자 충돌 문제 수정 |
| 오류 응답 | 허용 루트 외부 접근, 위험 명령 등 오류를 JSON으로 반환하도록 수정 |
| diff 출력 | `---`, `+++` 헤더 줄바꿈이 붙는 문제 수정 |
| 테스트 추가 | CLI 위험 명령 차단 및 경로 정책 오류 테스트 추가 |
| 버전 | `0.1.1`로 업데이트 |

## 5. 테스트 결과

| 검증 항목 | 결과 |
|---|---:|
| Python 문법 검사 | 통과 |
| 단위 테스트 | 통과, 7개 테스트 성공 |
| 샘플 프로젝트 CLI 플로우 | 통과 |
| 위험 명령 차단 | 통과 |
| 변경내용 `.md` 생성 | 통과 |
| ZIP 생성 | 통과 |

## 6. 주의사항

- MCP 서버로 사용하려면 로컬 PC에 `mcp` Python 패키지를 설치해야 합니다.
- 전체 C드라이브를 허용 루트로 지정하지 마세요.
- 민감파일과 시스템 경로는 기본 차단되어 있습니다.
- Windows 실제 경로와 ChatGPT/OpenCrab MCP 연결은 사용자 PC에서 최종 검증해야 합니다.
