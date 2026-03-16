# Know Where ERD

이 문서는 [PRD.md](/E:/Google%20Drive/VIBE_class/Know_where/PRD.md)를 기준으로 한 초기 데이터 모델 설계안이다.

## 1. 설계 원칙

- 로컬 단일 사용자 앱 기준으로 단순성을 우선한다.
- 검색, 비동기 처리, UI 상태 반영에 필요한 필드만 우선 포함한다.
- AI 확장을 위해 `summary`, `details`, `ingestion_status`는 미리 확보한다.

## 2. 엔터티 목록

- Folder
- Card
- Tag
- CardTag
- Job

## 3. 관계도

```text
Folder 1 --- N Card
Card   1 --- N CardTag
Tag    1 --- N CardTag
Card   1 --- N Job
```

## 4. 테이블 정의

### 4.1 folders

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| id | integer | pk | 폴더 ID |
| name | varchar(100) | not null | 폴더명 |
| slug | varchar(120) | unique, not null | 내부 식별자 |
| color | varchar(20) | null | UI 표시 색상 |
| sort_order | integer | not null, default 0 | 정렬 순서 |
| is_system | boolean | not null, default false | 시스템 폴더 여부 |
| created_at | datetime | not null | 생성시각 |
| updated_at | datetime | not null | 수정시각 |

규칙
- `전체`는 실제 row가 아닌 UI 가상 항목으로 처리
- `미분류`는 시스템 폴더 row로 저장
- 시스템 폴더는 삭제 불가

### 4.2 cards

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| id | integer | pk | 카드 ID |
| folder_id | integer | fk -> folders.id, not null | 소속 폴더 |
| url | text | not null | 원본 URL |
| normalized_url | text | not null | 정규화 URL |
| source_domain | varchar(255) | not null | 도메인 |
| title | varchar(500) | not null | 카드 제목 |
| summary | text | not null, default '' | 요약 |
| details | text | not null, default '' | 상세 내용 |
| memo | text | not null, default '' | 사용자 메모 |
| thumbnail_status | varchar(20) | not null, default 'pending' | 썸네일 상태 |
| thumbnail_path | text | null | 썸네일 파일 경로 |
| thumbnail_error | text | null | 최근 썸네일 실패 사유 |
| ingestion_status | varchar(20) | not null, default 'pending' | 메타데이터 수집 상태 |
| ingestion_error | text | null | 최근 수집 실패 사유 |
| tags_text | text | not null, default '' | 검색 최적화용 평탄화 태그 |
| created_at | datetime | not null | 생성시각 |
| updated_at | datetime | not null | 수정시각 |

규칙
- `title`은 사용자 입력이 없으면 서버가 fallback 생성
- `thumbnail_status`: `pending | processing | ready | failed`
- `ingestion_status`: `pending | processing | ready | failed`

### 4.3 tags

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| id | integer | pk | 태그 ID |
| name | varchar(100) | not null | 원본 태그명 |
| normalized_name | varchar(100) | unique, not null | 정규화 태그명 |
| created_at | datetime | not null | 생성시각 |

규칙
- normalize는 trim, lower, 다중 공백 축소 기준

### 4.4 card_tags

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| id | integer | pk | 연결 ID |
| card_id | integer | fk -> cards.id, not null | 카드 ID |
| tag_id | integer | fk -> tags.id, not null | 태그 ID |

제약
- unique(card_id, tag_id)

### 4.5 jobs

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| id | integer | pk | 작업 ID |
| job_type | varchar(50) | not null | 작업 유형 |
| target_type | varchar(50) | not null | 대상 타입 |
| target_id | integer | not null | 대상 ID |
| status | varchar(20) | not null, default 'queued' | 작업 상태 |
| priority | integer | not null, default 100 | 우선순위 |
| attempt_count | integer | not null, default 0 | 시도 횟수 |
| max_attempts | integer | not null, default 3 | 최대 재시도 |
| payload_json | text | null | 작업 payload |
| last_error | text | null | 최근 오류 |
| scheduled_at | datetime | not null | 실행 예정 시각 |
| started_at | datetime | null | 시작 시각 |
| finished_at | datetime | null | 종료 시각 |
| created_at | datetime | not null | 생성시각 |

규칙
- `job_type`: `fetch_metadata`, `generate_thumbnail`
- `status`: `queued | processing | done | failed`

## 5. 인덱스 설계

### folders
- unique index on `slug`
- index on `sort_order`

### cards
- index on `folder_id`
- index on `created_at desc`
- index on `normalized_url`
- index on `thumbnail_status`
- index on `ingestion_status`
- 복합 index on `(folder_id, created_at desc)`

### tags
- unique index on `normalized_name`

### card_tags
- unique index on `(card_id, tag_id)`
- index on `tag_id`

### jobs
- index on `(status, scheduled_at)`
- index on `(target_type, target_id)`
- index on `job_type`

## 6. 검색 설계 메모

초기 구현 2안이 가능하다.

### 안 1. 기본 LIKE 검색
- 구현이 가장 빠르다.
- 데이터가 적은 초기 단계에 충분하다.

### 안 2. SQLite FTS5
- 검색 속도와 확장성에 유리하다.
- title, memo, url, tags_text를 검색 인덱스로 관리할 수 있다.

권장안
- Phase 1은 LIKE 검색
- Phase 2 또는 3에서 FTS5로 전환

## 7. 데이터 무결성 규칙

- 카드 삭제 시 연결된 `card_tags`, `jobs`는 cascade delete
- 태그는 카드와의 연결이 사라져도 즉시 삭제하지 않아도 된다.
- 폴더 삭제 시 소속 카드는 `미분류` 폴더로 이동
- 시스템 폴더는 수정 범위를 제한한다.

## 8. 초기 데이터

### 시스템 폴더
- `uncategorized` / `미분류`

### UI 가상 폴더
- `all` / `전체`

`전체`는 DB row가 아니라 프론트 계산값으로 처리한다.

## 9. 다음 작업

- API 명세서 작성
- Django 모델 초안 생성
- 프론트 TypeScript 타입과 응답 DTO 맞추기
