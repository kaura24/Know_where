# Know Where - 개발 교훈

개발 중 실제로 겪은 문제와 그 해결 방식을 기록한다.

## 2026-03-16: `run_app_stack.ps1`에 데스크톱 창 실행 단계가 빠져 기본 실행이 불완전했다

### 현상

- `KnowWhere_WebApp.cmd` 또는 `run_app_stack.ps1` 실행 시 backend, worker, frontend는 떠 있었지만 주소창 없는 데스크톱 창이 보이지 않았다.
- 사용자 입장에서는 "앱이 실행되지 않는다"로 보였다.

### 원인

- `run_app_stack.ps1`가 서비스 3개만 띄우고 `run_desktop_app.ps1`를 호출하지 않았다.
- 문서에는 "기본 실행은 pywebview 데스크톱 창"이라고 적혀 있었지만 실제 실행 흐름은 그렇지 않았다.

### 해결

1. `desktop_app.py`에 `--no-start-services` 옵션을 추가했다.
2. `scripts/run_desktop_app.ps1`에 `-NoStartServices` 스위치를 추가했다.
3. `scripts/run_app_stack.ps1` 마지막 단계에서 `Start-DesktopApp -NoStartServices`를 호출하도록 고쳤다.
4. `scripts/RUN_STACK_CONTRACT.md`로 필수 실행 단계를 문서화했다.

### 검증

- `run_app_stack.ps1` 실행 후 backend, worker, frontend, desktop app 순으로 올라오는 흐름을 확인했다.
- `http://127.0.0.1:8000/api/health/` 응답을 확인했다.
- `http://127.0.0.1:5173` 응답을 확인했다.

### 교훈

- "기본 실행"은 서비스 실행만이 아니라 사용자가 실제 보는 창까지 포함해 정의해야 한다.
- 실행 스크립트는 계약 문서 없이 바꾸면 문서와 코드가 쉽게 어긋난다.

## 2026-03-16: 문서와 구현을 따로 관리하면 환경변수명과 검증 수치가 빠르게 틀어진다

### 현상

- `README.md`와 `AGENT_CONTEXT.md`의 테스트 수치가 현재 코드와 맞지 않았다.
- 루트 `.env.example`에는 `API_BASE_URL`이 있었지만, 프론트 실제 코드가 읽는 이름은 `VITE_API_BASE_URL`이었다.
- 현재 UI 기능인 검색 범위, 정렬, 폴더 이동, 태그 편집, 종료 API 등이 문서에 부분적으로만 반영돼 있었다.

### 원인

- 기능 구현과 테스트 추가는 계속 진행됐지만, 문서 갱신이 같은 시점에 묶여 있지 않았다.
- 환경변수 문서를 소비 코드가 아닌 기존 예시 파일 중심으로 유지했다.

### 해결

1. 백엔드 `pytest -q`, 프론트 `npm run build`를 다시 실행해 현재 기준 검증 수치를 확인했다.
2. `README.md`를 실행 방법, 환경변수, 구현 범위, 현재 리스크 기준으로 다시 정리했다.
3. `AGENT_CONTEXT.md`를 세션 로그 모음이 아니라 현재 상태 요약 문서로 재작성했다.
4. `.env.example`에서 잘못된 `API_BASE_URL` 예시를 정리하고, 프론트 override는 `frontend/.env.local`의 `VITE_API_BASE_URL`로 안내하도록 바꿨다.

### 교훈

- 문서는 릴리스 노트가 아니라 현재 코드의 운영 인터페이스여야 한다.
- 환경변수명은 반드시 실제 소비 코드에서 역으로 확인해야 한다.
- 커밋 전에 테스트 숫자, 실행 엔트리, 환경변수 이름은 한 번 더 재검증해야 한다.
