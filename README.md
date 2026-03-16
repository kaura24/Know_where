# Know Where

Know Where는 URL을 저장하면 메타데이터, 요약, 태그, 썸네일을 카드로 정리해 주는 로컬 단일 사용자용 지식 카드 앱이다. 백엔드는 Django + DRF + SQLite, 프론트엔드는 React + TypeScript + Vite, 데스크톱 모드는 `pywebview`를 사용한다.

## 현재 구현 범위

- URL 저장 시 `fetch_metadata`, `generate_thumbnail` 작업을 큐에 등록한다.
- 카드 목록/상세/수정/삭제가 연결돼 있다.
- 검색은 `title`, `url`, `summary`, `details`, `memo`, `tags_text`를 기준으로 동작한다.
- 정렬은 `최신순(created_at_desc)`, `오래된순(created_at_asc)`를 지원한다.
- 시스템 폴더 `미분류`, `코딩`, `여행`, `업무`를 사용한다.
- 신규 저장 시 명시적 폴더가 없으면 규칙 기반 자동 분류를 먼저 적용한다.
- 커스텀 폴더 생성/삭제를 지원하며, 삭제 시 카드들은 `미분류`로 이동한다.
- 카드 상세에서 `title`, `details`, `memo`, `tags`를 수정할 수 있다.
- 카드 새로고침은 `/api/cards/{id}/retry-jobs/`를 호출해 메타데이터/썸네일 작업을 다시 큐잉한다.
- AI 요약/태그/폴더 재분류는 메타데이터 작업 경로에서만 선택적으로 동작한다.
- AI 호출은 `신규 저장`과 `새로고침(retry-jobs)`에서만 허용된다.
- 수동 `generate-tags` 액션은 정책상 막혀 있으며 `409 AI_POLICY_RESTRICTED`를 반환한다.
- 프론트엔드는 폴더 필터, 검색, 정렬, 드래그 앤 드롭 폴더 이동, 상세 오버레이, UI 버전 전환, 테마 전환, 앱 줌, 안전 종료 버튼을 포함한다.
- 기본 실행은 주소창 없는 `pywebview` 창이며, 브라우저 모드 실행도 가능하다.

## 프로젝트 구조

- `backend/`: Django API, SQLite DB, worker command, media 저장소
- `frontend/`: React + Vite UI, Playwright E2E
- `scripts/`: Windows PowerShell 실행/종료 스택, OS 감지 Python 엔트리
- `desktop_app.py`: `pywebview` 기반 데스크톱 셸
- `AGENT_CONTEXT.md`: 현재 구현 컨텍스트
- `LESSON.md`: 개발 중 발견한 이슈와 교훈
- `API_SPEC.md`: API 계약 초안
- `TODO.md`: 남은 작업 우선순위

## 요구 사항

- Python 3.13 계열 권장
- Node.js 20+ 권장
- Windows에서 기본 스크립트를 쓰려면 PowerShell 7
- 썸네일 생성과 일부 메타데이터 fallback, E2E를 위해 Playwright Chromium 필요
- 데스크톱 모드는 `pywebview`와 Windows WebView 환경이 필요

## 빠른 실행

권장 진입점은 루트에서 아래 두 명령이다.

```powershell
python .\scripts\run_app_stack.py
python .\scripts\stop_app_stack.py
```

Windows에서는 `run_app_stack.py`가 내부적으로 `scripts/run_app_stack.ps1`를 호출하고, 아래 순서로 실행한다.

1. 기존 스택 안전 종료
2. 백엔드 실행
3. 워커 실행
4. 프론트 실행
5. `pywebview` 데스크톱 창 실행

더블클릭 실행도 가능하다.

- `KnowWhere_WebApp.cmd`: 기본 웹앱 실행
- `KnowWhere_Browser.cmd`: 브라우저 모드 실행

## 수동 설치 및 실행

### 1. 백엔드

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

### 2. 워커

```powershell
cd backend
python manage.py run_worker
```

원샷 처리:

```powershell
cd backend
python manage.py run_worker --once
```

### 3. 프론트엔드

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

### 4. 데스크톱 앱 직접 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_desktop_app.ps1
```

이미 백엔드/워커/프론트가 떠 있는 상태에서 창만 열고 싶으면:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_desktop_app.ps1 -NoStartServices
```

## 스크립트 역할

- `scripts/run_app_stack.py`: OS 감지형 공통 실행 진입점
- `scripts/stop_app_stack.py`: OS 감지형 공통 종료 진입점
- `scripts/run_app_stack.ps1`: Windows 기본 실행, 서비스 3개와 데스크톱 창을 순차 실행
- `scripts/run_browser_stack.ps1`: 기본 스택 실행 후 Chrome 새 창 열기
- `scripts/run_desktop_app.ps1`: `pywebview` 데스크톱 창 실행
- `scripts/run_backend.ps1`: Django API 서버 실행 및 헬스 체크
- `scripts/run_worker.ps1`: worker 프로세스 실행
- `scripts/run_frontend.ps1`: Vite 개발 서버 실행 및 헬스 체크
- `scripts/stop_app_stack.ps1`: 추적 PID와 포트를 기준으로 전체 스택 종료
- `scripts/open_browser.ps1`: `http://127.0.0.1:5173`를 Chrome 새 창으로 열기
- `scripts/app_control_panel.ps1`: 실행/브라우저/종료 버튼이 있는 Windows 제어 패널

`scripts/RUN_STACK_CONTRACT.md`는 `run_app_stack.ps1`의 필수 단계 계약 문서다.

## 설정

### 백엔드 환경변수

루트 `.env`를 사용한다. 기본값 예시는 [.env.example](/E:/Google%20Drive/VIBE_class/Know_where/.env.example)에 있다.

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL_SUMMARY`
- `OPENAI_BASE_URL`
- `OPENAI_TIMEOUT_SECONDS`
- `AI_SUMMARY_ENABLED`

### 프론트엔드 API 주소

프론트는 기본적으로 `http://localhost:8000/api`를 사용한다. 다른 주소를 쓰려면 `frontend/.env.local`에 아래 값을 둔다.

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## API 표면

- `GET /api/health/`
- `POST /api/health/shutdown/`
- `GET/POST/DELETE /api/folders/`
- `GET/POST/PATCH/DELETE /api/cards/`
- `GET /api/cards/{id}/status/`
- `POST /api/cards/{id}/retry-jobs/`
- `POST /api/cards/{id}/generate-tags/` -> 현재 정책상 `409`

카드 목록 쿼리 파라미터:

- `folder_id`
- `q`
- `sort=created_at_desc|created_at_asc`

## 테스트와 검증

2026-03-16 기준으로 아래 검증을 다시 실행했다.

```powershell
cd backend
pytest -q

cd ..\frontend
npm run build
```

결과:

- 백엔드 테스트 `16 passed`
- 프론트 production build 성공

`frontend/tests/e2e/app.spec.ts`는 카드 생성 후 상세 오버레이를 여는 메인 happy path만 다룬다. 실패/재시도 시나리오는 아직 부족하다.

## 현재 주의사항

- URL 정규화는 아직 `strip()` 수준이라 강화 여지가 크다.
- SSRF 방어는 아직 없다.
- 표준 에러 포맷은 일부 엔드포인트만 맞춰져 있다.
- AI 품질과 자동 폴더 재분류는 아직 튜닝 중이다.
- 프론트 optimistic UX와 에러 토스트는 보강 여지가 있다.
- `npm run build`는 `frontend/dist` 산출물을 갱신한다.

## 참고 문서

- [AGENT_CONTEXT.md](/E:/Google%20Drive/VIBE_class/Know_where/AGENT_CONTEXT.md)
- [LESSON.md](/E:/Google%20Drive/VIBE_class/Know_where/LESSON.md)
- [API_SPEC.md](/E:/Google%20Drive/VIBE_class/Know_where/API_SPEC.md)
- [TODO.md](/E:/Google%20Drive/VIBE_class/Know_where/TODO.md)
