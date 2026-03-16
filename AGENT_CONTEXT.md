# Know Where Agent Context

이 문서는 현재 저장소 상태를 빠르게 파악하기 위한 작업 컨텍스트다. 세션 로그 대신 현재 코드 기준 사실만 남긴다.

## 1. 제품 요약

- 로컬 단일 사용자용 지식 카드 앱이다.
- URL을 저장하면 카드가 생성되고, 메타데이터/요약/썸네일 작업이 백그라운드로 처리된다.
- 백엔드는 Django + DRF + SQLite, 프론트는 React + TypeScript + Vite다.
- 데스크톱 모드는 `pywebview`, 브라우저 모드는 일반 Chrome 창을 사용한다.

## 2. 현재 구현된 핵심 기능

- 카드 생성, 목록, 상세 조회, 부분 수정, 삭제
- 폴더 생성/삭제
- 시스템 폴더 `미분류`, `코딩`, `여행`, `업무`
- 규칙 기반 초기 자동 분류
- 검색: `title`, `url`, `summary`, `details`, `memo`, `tags_text`
- 정렬: `created_at_desc`, `created_at_asc`
- 카드 폴더 이동
- 카드 상세에서 `title`, `details`, `memo`, `tags` 수정
- 메타데이터/썸네일 작업 재시도
- UI 버전 전환, 테마 전환, 줌, 안전 종료 버튼

## 3. 런타임 구조

권장 실행:

- `python scripts/run_app_stack.py`
- `python scripts/stop_app_stack.py`

Windows 실행 흐름:

1. `scripts/run_app_stack.py`
2. `scripts/run_app_stack.ps1`
3. `scripts/stop_app_stack.ps1`
4. `scripts/run_backend.ps1`
5. `scripts/run_worker.ps1`
6. `scripts/run_frontend.ps1`
7. `Start-DesktopApp -NoStartServices`

관련 파일:

- [scripts/run_app_stack.py](/E:/Google%20Drive/VIBE_class/Know_where/scripts/run_app_stack.py)
- [scripts/stop_app_stack.py](/E:/Google%20Drive/VIBE_class/Know_where/scripts/stop_app_stack.py)
- [scripts/run_app_stack.ps1](/E:/Google%20Drive/VIBE_class/Know_where/scripts/run_app_stack.ps1)
- [scripts/common.ps1](/E:/Google%20Drive/VIBE_class/Know_where/scripts/common.ps1)
- [scripts/RUN_STACK_CONTRACT.md](/E:/Google%20Drive/VIBE_class/Know_where/scripts/RUN_STACK_CONTRACT.md)
- [desktop_app.py](/E:/Google%20Drive/VIBE_class/Know_where/desktop_app.py)

비고:

- Windows에서는 `run_app_stack.ps1`가 데스크톱 창 실행까지 포함한다.
- macOS/Linux에서는 `run_app_stack.py`가 `desktop_app.py`를 직접 띄운다.
- `desktop_app.py`는 기본적으로 backend, worker, frontend를 직접 띄울 수 있고 `--no-start-services` 모드도 지원한다.

## 4. 백엔드 요약

주요 URL:

- `GET /api/health/`
- `POST /api/health/shutdown/`
- `GET/POST /api/folders/`
- `DELETE /api/folders/{id}/`
- `GET/POST /api/cards/`
- `GET/PATCH/DELETE /api/cards/{id}/`
- `GET /api/cards/{id}/status/`
- `POST /api/cards/{id}/retry-jobs/`
- `POST /api/cards/{id}/generate-tags/`

카드 모델 핵심 필드:

- `folder`
- `url`, `normalized_url`, `source_domain`
- `title`, `summary`, `details`, `memo`
- `thumbnail_status`, `thumbnail_path`, `thumbnail_error`
- `ingestion_status`, `ingestion_error`
- `tags`, `tags_text`
- `created_at`, `updated_at`

폴더 동작:

- 시스템 폴더는 삭제 불가
- 사용자 폴더 삭제 시 카드들을 `uncategorized`로 이동
- 폴더 리스트는 `card_count` annotate 결과를 포함

카드 리스트 파라미터:

- `folder_id`
- `q`
- `sort=created_at_desc|created_at_asc`

## 5. 작업 큐와 AI 정책

카드 생성 시:

- `fetch_metadata`
- `generate_thumbnail`

두 작업을 `Job` 테이블에 큐잉한다.

메타데이터 작업:

- HTML title/meta description/OG 데이터 파싱
- article/main/p 요소 기반 본문 추출
- Threads 계열 URL은 static article text가 비어 있으면 Playwright 렌더링 fallback 사용
- 결과를 `title`, `summary`, `details`에 반영
- 태그가 비어 있으면 텍스트 기반 태그 생성 fallback 수행
- 카드가 `uncategorized`면 AI 분류 결과에 따라 `coding`, `travel`, `work`로 재배치 가능

AI 정책:

- `AI_SUMMARY_ENABLED=True` 이고 `OPENAI_API_KEY`가 있을 때만 동작
- 호출 위치는 `신규 저장(create)`와 `retry-jobs` 경로의 메타데이터 작업뿐이다
- `folder_id` 변경, 상세 편집, 수동 `generate-tags`에서는 AI를 호출하지 않는다
- `/api/cards/{id}/generate-tags/`는 현재 고정적으로 `409 AI_POLICY_RESTRICTED`를 반환한다

## 6. 프론트엔드 요약

페이지:

- 단일 메인 화면 중심 구조
- 카드 목록과 상세 오버레이를 함께 사용

현재 확인된 프론트 동작:

- 폴더 필터
- 검색 입력
- 생성일 기준 정렬
- 저장 후 카드 처리 상태 추적
- 폴더 직접 선택 및 드래그 앤 드롭 이동
- 상세에서 메모/상세/태그 편집
- 목록/상세에서 새로고침, 삭제
- `old/new` UI 버전 전환
- UI 테마 3종, 색상 테마 3종
- `Ctrl + wheel`, `Ctrl + +`, `Ctrl + -`, `Ctrl + 0` 줌
- 우상단 종료 버튼에서 `/api/health/shutdown/` 호출

React Query:

- 카드 목록/상세는 작업 상태가 `pending` 또는 `processing`일 때 5초 간격 polling
- 카드/폴더 변경 시 관련 query invalidate 처리

## 7. 환경변수와 설정

백엔드:

- 루트 `.env` 사용
- 실제 로딩 위치는 [backend/know_where_backend/settings.py](/E:/Google%20Drive/VIBE_class/Know_where/backend/know_where_backend/settings.py)

지원 변수:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL_SUMMARY`
- `OPENAI_BASE_URL`
- `OPENAI_TIMEOUT_SECONDS`
- `AI_SUMMARY_ENABLED`

프론트:

- 기본 API 주소는 `http://localhost:8000/api`
- override가 필요하면 `frontend/.env.local`에 `VITE_API_BASE_URL` 사용

## 8. 검증 현황

2026-03-16에 재검증한 결과:

- `backend`: `pytest -q` -> `16 passed`
- `frontend`: `npm run build` 성공

현재 자동화 범위:

- 백엔드 테스트는 카드 생성, 재시도, 검색, 정렬, AI 정책, Threads fallback, 자동 재분류 등을 다룬다.
- 프론트 E2E는 카드 생성 후 상세 오버레이 진입 happy path 1개만 있다.

## 9. 남은 리스크

- URL 정규화가 아직 약하다.
- SSRF 방어가 없다.
- 표준 에러 포맷이 일관되지 않다.
- AI 프롬프트/분류 품질은 계속 튜닝 중이다.
- 프론트 실패 UX와 토스트가 약하다.
- E2E가 happy path 중심이라 실패/재시도/종료 시나리오가 부족하다.

## 10. 문서 수정 시 체크포인트

- 실행 관련 변경은 `README.md`, `AGENT_CONTEXT.md`, `LESSON.md`, `scripts/RUN_STACK_CONTRACT.md`를 같이 확인한다.
- AI 정책 변경은 `backend/apps/cards/views.py`, `backend/apps/cards/services.py`, `backend/apps/jobs/services.py`, `backend/apps/jobs/ai_summary.py`를 같이 확인한다.
- 환경변수 문서는 소비 코드 이름과 정확히 일치해야 한다.
