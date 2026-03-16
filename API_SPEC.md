# Know Where API Spec

이 문서는 [PRD.md](/E:/Google%20Drive/VIBE_class/Know_where/PRD.md)와 [ERD.md](/E:/Google%20Drive/VIBE_class/Know_where/ERD.md)를 기준으로 한 프론트/백엔드 계약 문서다.

## 1. 기본 규칙

- Base URL: `/api`
- Content-Type: `application/json`
- 인증 없음
- 시간 포맷: ISO 8601 with timezone
- 정렬 기본값: `created_at_desc`

## 2. 공통 응답 규칙

### 2.1 성공 응답
- 목록은 pagination envelope 사용
- 단건은 리소스 객체 그대로 반환

### 2.2 에러 응답

```json
{
  "code": "INVALID_URL",
  "message": "유효한 URL이 아닙니다.",
  "details": {}
}
```

### 2.3 공통 에러 코드

| code | 의미 | http status |
| --- | --- | --- |
| INVALID_URL | URL 형식 오류 | 400 |
| INVALID_FOLDER | 존재하지 않거나 사용할 수 없는 폴더 | 400 |
| INVALID_TAGS | 태그 입력 오류 | 400 |
| NOT_FOUND | 대상 리소스 없음 | 404 |
| CONFLICT | 중복 또는 상태 충돌 | 409 |
| INTERNAL_ERROR | 서버 내부 오류 | 500 |

## 3. 공통 타입

### 3.1 Folder

```json
{
  "id": 1,
  "name": "개발",
  "slug": "development",
  "color": "blue",
  "sort_order": 10,
  "is_system": false,
  "card_count": 12,
  "created_at": "2026-03-13T11:00:00+09:00",
  "updated_at": "2026-03-13T11:00:00+09:00"
}
```

### 3.2 CardListItem

```json
{
  "id": 101,
  "folder_id": 1,
  "folder_name": "개발",
  "url": "https://react.dev",
  "source_domain": "react.dev",
  "title": "React 공식 문서",
  "summary": "React 문서 요약",
  "memo": "팀 공유 예정",
  "tags": ["react", "frontend"],
  "has_memo": true,
  "thumbnail_status": "ready",
  "thumbnail_url": "/media/thumbnails/2026/03/101.jpg",
  "ingestion_status": "ready",
  "created_at": "2026-03-13T11:10:00+09:00",
  "updated_at": "2026-03-13T11:12:00+09:00"
}
```

### 3.3 CardDetail

```json
{
  "id": 101,
  "folder_id": 1,
  "folder_name": "개발",
  "url": "https://react.dev",
  "normalized_url": "https://react.dev/",
  "source_domain": "react.dev",
  "title": "React 공식 문서",
  "summary": "React 문서 요약",
  "details": "상세 설명",
  "memo": "팀 공유 예정",
  "tags": ["react", "frontend"],
  "thumbnail_status": "ready",
  "thumbnail_url": "/media/thumbnails/2026/03/101.jpg",
  "ingestion_status": "ready",
  "created_at": "2026-03-13T11:10:00+09:00",
  "updated_at": "2026-03-13T11:12:00+09:00"
}
```

### 3.4 JobStatus

```json
{
  "card_id": 101,
  "thumbnail_status": "processing",
  "ingestion_status": "ready",
  "thumbnail_error": null,
  "ingestion_error": null,
  "updated_at": "2026-03-13T11:12:00+09:00"
}
```

### 3.5 Pagination

```json
{
  "count": 124,
  "next": "/api/cards?page=2&page_size=20",
  "previous": null,
  "results": []
}
```

## 4. 폴더 API

### 4.1 `GET /api/folders`

설명
- 폴더 목록 조회
- `전체`는 프론트 가상 항목이므로 API 응답에는 포함하지 않음

응답

```json
[
  {
    "id": 1,
    "name": "미분류",
    "slug": "uncategorized",
    "color": "gray",
    "sort_order": 0,
    "is_system": true,
    "card_count": 5,
    "created_at": "2026-03-13T11:00:00+09:00",
    "updated_at": "2026-03-13T11:00:00+09:00"
  }
]
```

### 4.2 `POST /api/folders`

request

```json
{
  "name": "AI & Data",
  "color": "emerald"
}
```

validation
- `name` 필수
- 길이 1~100
- 사용자 폴더 이름 중복 금지 권장

response
- `201 Created`

### 4.3 `PATCH /api/folders/{id}`

request

```json
{
  "name": "AI",
  "color": "green",
  "sort_order": 30
}
```

validation
- 시스템 폴더는 이름 변경 범위를 제한 가능

### 4.4 `DELETE /api/folders/{id}`

설명
- 시스템 폴더 삭제 불가
- 삭제 대상 폴더의 카드들은 `미분류`로 이동

response
- `204 No Content`

## 5. 카드 API

### 5.1 `GET /api/cards`

설명
- 카드 목록 조회
- 기본 정렬은 최신순

query params

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| folder_id | integer | 특정 폴더 필터 |
| q | string | title/url/memo/tags 대상 통합 검색 |
| sort | string | `created_at_desc`, `created_at_asc` |
| page | integer | 페이지 번호 |
| page_size | integer | 페이지 크기, 기본 20 |

response

```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 101,
      "folder_id": 1,
      "folder_name": "개발",
      "url": "https://react.dev",
      "source_domain": "react.dev",
      "title": "React 공식 문서",
      "summary": "React 문서 요약",
      "memo": "팀 공유 예정",
      "tags": ["react", "frontend"],
      "has_memo": true,
      "thumbnail_status": "processing",
      "thumbnail_url": null,
      "ingestion_status": "ready",
      "created_at": "2026-03-13T11:10:00+09:00",
      "updated_at": "2026-03-13T11:12:00+09:00"
    }
  ]
}
```

### 5.2 `POST /api/cards`

설명
- 카드 생성
- 카드 생성 자체는 즉시 완료
- 메타데이터 수집/썸네일은 비동기

request

```json
{
  "folder_id": 1,
  "url": "https://react.dev",
  "title": "",
  "summary": "",
  "details": "",
  "memo": "팀 발표 참고",
  "tags": ["react", "frontend"]
}
```

validation
- `url` 필수
- `folder_id`는 생략 가능, 생략 시 `미분류`
- tags는 문자열 배열
- 빈 title 허용

response
- `201 Created`

```json
{
  "id": 101,
  "folder_id": 1,
  "folder_name": "미분류",
  "url": "https://react.dev",
  "normalized_url": "https://react.dev/",
  "source_domain": "react.dev",
  "title": "react.dev 문서",
  "summary": "",
  "details": "",
  "memo": "팀 발표 참고",
  "tags": ["react", "frontend"],
  "thumbnail_status": "pending",
  "thumbnail_url": null,
  "ingestion_status": "pending",
  "created_at": "2026-03-13T11:15:00+09:00",
  "updated_at": "2026-03-13T11:15:00+09:00"
}
```

### 5.3 `GET /api/cards/{id}`

설명
- 카드 상세 조회
- 상세 모달 진입 시 사용

response
- `200 OK`
- 응답 형식은 `CardDetail`

### 5.4 `PATCH /api/cards/{id}`

설명
- 부분 수정
- 메모, 제목, summary, details, folder, tags 수정 가능

request 예시

```json
{
  "memo": "업데이트된 메모"
}
```

또는

```json
{
  "folder_id": 2,
  "title": "React 문서 다시 보기",
  "tags": ["react", "docs"]
}
```

response
- `200 OK`
- 응답 형식은 `CardDetail`

### 5.5 `DELETE /api/cards/{id}`

설명
- 카드 삭제

response
- `204 No Content`

## 6. 작업 상태 API

### 6.1 `GET /api/cards/{id}/status`

설명
- 썸네일/메타데이터 비동기 처리 상태 조회
- 프론트 polling 용도

response

```json
{
  "card_id": 101,
  "thumbnail_status": "ready",
  "ingestion_status": "ready",
  "thumbnail_error": null,
  "ingestion_error": null,
  "updated_at": "2026-03-13T11:20:00+09:00"
}
```

## 7. 프론트 구현용 타입 매핑

### 7.1 TypeScript Folder

```ts
export interface Folder {
  id: number;
  name: string;
  slug: string;
  color: string | null;
  sort_order: number;
  is_system: boolean;
  card_count: number;
  created_at: string;
  updated_at: string;
}
```

### 7.2 TypeScript CardListItem

```ts
export interface CardListItem {
  id: number;
  folder_id: number;
  folder_name: string;
  url: string;
  source_domain: string;
  title: string;
  summary: string;
  memo: string;
  tags: string[];
  has_memo: boolean;
  thumbnail_status: 'pending' | 'processing' | 'ready' | 'failed';
  thumbnail_url: string | null;
  ingestion_status: 'pending' | 'processing' | 'ready' | 'failed';
  created_at: string;
  updated_at: string;
}
```

### 7.3 TypeScript CardDetail

```ts
export interface CardDetail extends CardListItem {
  normalized_url: string;
  details: string;
}
```

### 7.4 TypeScript Create/Patch Payload

```ts
export interface CreateCardPayload {
  folder_id?: number;
  url: string;
  title?: string;
  summary?: string;
  details?: string;
  memo?: string;
  tags?: string[];
}

export interface UpdateCardPayload {
  folder_id?: number;
  title?: string;
  summary?: string;
  details?: string;
  memo?: string;
  tags?: string[];
}
```

## 8. 프론트 연동 메모

- 카드 목록은 `GET /api/cards`
- 폴더 목록은 `GET /api/folders`
- 카드 생성은 optimistic update 가능
- 상세 모달 open 시 `GET /api/cards/{id}` 재조회 권장
- 썸네일 또는 메타데이터가 `pending/processing`이면 `GET /api/cards/{id}/status` polling 가능

## 9. 구현 순서 권장

1. 폴더 목록 API
2. 카드 목록 API
3. 카드 생성 API
4. 카드 상세/수정/삭제 API
5. 상태 조회 API
6. 검색 최적화
