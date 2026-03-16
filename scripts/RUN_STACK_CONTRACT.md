# run_app_stack.ps1 실행 계약

이 문서는 `run_app_stack.ps1`의 **필수 실행 단계**를 정의한다.  
수정 시 이 계약을 준수해야 하며, 누락 시 KnowWhere_WebApp.cmd 실행 시 앱 창이 뜨지 않는 오류가 재발한다.

## 필수 단계 (순서 고정)

1. **stop_app_stack.ps1** — 기존 서비스 정리
2. **run_backend.ps1** — Django API 서버 기동
3. **run_worker.ps1** — 메타데이터/썸네일 워커 기동
4. **run_frontend.ps1** — Vite 개발 서버 기동
5. **run_desktop_app.ps1 -NoStartServices** — pywebview 데스크톱 앱 창 실행 **(필수, 생략 금지)**

## 주의

- 5단계를 제거하거나 주석 처리하면 서버만 떠 있고 **앱 창이 표시되지 않음**
- `run_desktop_app.ps1`은 반드시 `-NoStartServices`로 호출 (이미 2~4단계에서 서비스가 띄워진 상태)
- 관련 문서: [LESSON.md](../LESSON.md), [AGENT_CONTEXT.md](../AGENT_CONTEXT.md) 섹션 13
