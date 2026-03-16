from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cards.models import Card
from apps.folders.models import Folder
from apps.jobs import services as job_services
from apps.jobs.models import Job
from apps.cards import services as card_services
from apps.jobs.ai_summary import SummaryResult


@pytest.mark.django_db
def test_create_card_enqueues_jobs():
    client = APIClient()

    response = client.post(
        "/api/cards/",
        {"url": "https://example.com", "memo": "pytest"},
        format="json",
    )

    assert response.status_code == 201
    card_id = response.json()["id"]
    job_types = list(
        Job.objects.filter(target_id=card_id).order_by("job_type").values_list("job_type", flat=True)
    )
    assert job_types == ["fetch_metadata", "generate_thumbnail"]


@pytest.mark.django_db
def test_retry_jobs_resets_failed_status():
    client = APIClient()
    create_response = client.post(
        "/api/cards/",
        {"url": "https://example.com"},
        format="json",
    )
    card_id = create_response.json()["id"]
    card = Card.objects.get(id=card_id)
    card.thumbnail_status = Card.ProcessingStatus.FAILED
    card.ingestion_status = Card.ProcessingStatus.FAILED
    card.thumbnail_error = "thumb failed"
    card.ingestion_error = "meta failed"
    card.save()
    Job.objects.filter(target_id=card_id).update(status=Job.JobStatus.FAILED, last_error="failed")

    retry_response = client.post(f"/api/cards/{card_id}/retry-jobs/")

    assert retry_response.status_code == 200
    card.refresh_from_db()
    assert card.thumbnail_status == Card.ProcessingStatus.PENDING
    assert card.ingestion_status == Card.ProcessingStatus.PENDING
    assert card.thumbnail_error is None
    assert card.ingestion_error is None
    assert set(Job.objects.filter(target_id=card_id).values_list("status", flat=True)) == {"queued"}


@pytest.mark.django_db
def test_create_card_auto_classifies_coding_folder():
    client = APIClient()

    response = client.post(
        "/api/cards/",
        {"url": "https://react.dev/learn", "tags": ["typescript"]},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["folder_name"] == "코딩"


@pytest.mark.django_db
def test_create_card_auto_classifies_travel_folder():
    client = APIClient()

    response = client.post(
        "/api/cards/",
        {"url": "https://example.com/seoul-trip-guide", "memo": "여행 일정과 호텔 후보"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["folder_name"] == "여행"


@pytest.mark.django_db
def test_create_card_keeps_explicit_folder_over_auto_classification():
    client = APIClient()
    work_folder = Folder.objects.get(slug="work")

    response = client.post(
        "/api/cards/",
        {"url": "https://github.com/example/project", "folder_id": work_folder.id},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["folder_name"] == "업무"


@pytest.mark.django_db
def test_create_card_falls_back_to_uncategorized_when_not_classifiable():
    client = APIClient()

    response = client.post(
        "/api/cards/",
        {"url": "https://example.com/random-note", "memo": "분류 키워드가 거의 없는 일반 링크"},
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["folder_name"] == "미분류"


@pytest.mark.django_db
def test_update_card_details_does_not_trigger_ai_tag_generation(monkeypatch):
    client = APIClient()
    create_response = client.post(
        "/api/cards/",
        {"url": "https://example.com/details-tag-test"},
        format="json",
    )
    card_id = create_response.json()["id"]

    monkeypatch.setattr(
        card_services,
        "sync_tags",
        lambda card, tags: (_ for _ in ()).throw(AssertionError("sync_tags should not be called when updating details only")),
    )

    response = client.patch(
        f"/api/cards/{card_id}/",
        {"details": "React useEffect와 cleanup, dependencies에 대한 상세 설명"},
        format="json",
    )

    assert response.status_code == 200
    card = Card.objects.get(id=card_id)
    assert card.details == "React useEffect와 cleanup, dependencies에 대한 상세 설명"
    assert list(card.tags.values_list("name", flat=True)) == []


@pytest.mark.django_db
def test_generate_tags_action_is_policy_restricted():
    client = APIClient()
    create_response = client.post(
        "/api/cards/",
        {"url": "https://example.com/tag-action-test", "details": "초기 상세 내용"},
        format="json",
    )
    card_id = create_response.json()["id"]

    response = client.post(f"/api/cards/{card_id}/generate-tags/")

    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "AI_POLICY_RESTRICTED"


@pytest.mark.django_db
def test_list_cards_supports_created_at_sorting():
    client = APIClient()
    folder = Folder.objects.get(slug="uncategorized")
    old_card = Card.objects.create(
        folder=folder,
        url="https://example.com/old",
        normalized_url="https://example.com/old",
        source_domain="example.com",
        title="Old card",
    )
    new_card = Card.objects.create(
        folder=folder,
        url="https://example.com/new",
        normalized_url="https://example.com/new",
        source_domain="example.com",
        title="New card",
    )
    Card.objects.filter(id=old_card.id).update(created_at=timezone.now() - timedelta(days=1))
    Card.objects.filter(id=new_card.id).update(created_at=timezone.now())

    asc_response = client.get("/api/cards/?sort=created_at_asc")
    assert asc_response.status_code == 200
    asc_ids = [item["id"] for item in asc_response.json()["results"][:2]]
    assert asc_ids == [old_card.id, new_card.id]

    desc_response = client.get("/api/cards/?sort=created_at_desc")
    assert desc_response.status_code == 200
    desc_ids = [item["id"] for item in desc_response.json()["results"][:2]]
    assert desc_ids == [new_card.id, old_card.id]


@pytest.mark.django_db
def test_list_cards_search_matches_details_field():
    client = APIClient()
    folder = Folder.objects.get(slug="uncategorized")
    target = Card.objects.create(
        folder=folder,
        url="https://example.com/detail-search",
        normalized_url="https://example.com/detail-search",
        source_domain="example.com",
        title="Detail search target",
        details="react hook cleanup sequence",
    )
    Card.objects.create(
        folder=folder,
        url="https://example.com/other-card",
        normalized_url="https://example.com/other-card",
        source_domain="example.com",
        title="Other card",
        details="no keyword",
    )

    response = client.get("/api/cards/?q=cleanup")
    assert response.status_code == 200
    result_ids = {item["id"] for item in response.json()["results"]}
    assert target.id in result_ids


@pytest.mark.django_db
def test_metadata_job_reclassifies_uncategorized_card_to_coding(monkeypatch):
    card = Card.objects.create(
        folder=Folder.objects.get(slug="uncategorized"),
        url="https://example.com/dev-tool",
        normalized_url="https://example.com/dev-tool",
        source_domain="example.com",
        title="example.com 문서",
    )

    monkeypatch.setattr(
        job_services,
        "_fetch_metadata",
        lambda url: {
            "title": "ExtractCSS guide",
            "description": "design tool",
            "og:title": "",
            "og:description": "",
            "og:image": "",
            "article_text": "ExtractCSS is a Chrome extension for vibe design and Tailwind extraction.",
            "article_excerpt": "ExtractCSS Tailwind extraction guide",
        },
    )
    monkeypatch.setattr(
        job_services,
        "generate_summary_details",
        lambda **kwargs: type(
            "Result",
            (),
            {
                "title": "바이브 디자인을 위한 툴_ ExtractCSS라는 크롬 익스텐션",
                "summary": "Tailwind 추출 도구 설명",
                "details": "크롬 익스텐션으로 웹 요소에서 Tailwind 코드를 추출한다.",
                "tags": ["ExtractCSS", "Tailwind", "Chrome Extension", "Vibe Design"],
            },
        )(),
    )
    monkeypatch.setattr(job_services, "classify_folder_from_content", lambda **kwargs: "coding")

    job = Job.objects.create(
        job_type="fetch_metadata",
        target_type="card",
        target_id=card.id,
        scheduled_at=timezone.now(),
        payload_json={"card_id": card.id},
    )

    job_services._handle_metadata_job(job)

    card.refresh_from_db()
    assert card.folder.slug == "coding"


@pytest.mark.django_db
def test_metadata_job_prefers_ai_title_over_source_title(monkeypatch):
    card = Card.objects.create(
        folder=Folder.objects.get(slug="uncategorized"),
        url="https://threads.net/example/post",
        normalized_url="https://threads.net/example/post",
        source_domain="threads.net",
        title="threads.net 문서",
    )

    monkeypatch.setattr(
        job_services,
        "_fetch_metadata",
        lambda url: {
            "title": "github.trending (@github.trending) on Threads",
            "description": "ExtractCSS라는 크롬 익스텐션으로 Tailwind 코드를 추출하는 사용법 소개",
            "og:title": "",
            "og:description": "바이브 디자인을 위한 툴 소개와 사용법",
            "og:image": "",
            "article_text": "",
            "article_excerpt": "",
        },
    )
    monkeypatch.setattr(
        job_services,
        "generate_summary_details",
        lambda **kwargs: SummaryResult(
            title="바이브 디자인을 위한 툴_ ExtractCSS라는 크롬 익스텐션",
            summary="Tailwind 추출을 빠르게 수행하는 도구 소개",
            details="익스텐션을 켜고 요소를 클릭하면 Tailwind 코드를 추출할 수 있다.",
            tags=["ExtractCSS", "Tailwind", "Chrome Extension"],
        ),
    )
    monkeypatch.setattr(job_services, "classify_folder_from_content", lambda **kwargs: None)

    job = Job.objects.create(
        job_type="fetch_metadata",
        target_type="card",
        target_id=card.id,
        scheduled_at=timezone.now(),
        payload_json={"card_id": card.id},
    )

    job_services._handle_metadata_job(job)

    card.refresh_from_db()
    assert card.title == "바이브 디자인을 위한 툴_ ExtractCSS라는 크롬 익스텐션"


@pytest.mark.django_db
def test_card_detail_returns_ai_generated_title_after_metadata_job(monkeypatch):
    client = APIClient()
    create_response = client.post(
        "/api/cards/",
        {"url": "https://threads.net/example/post"},
        format="json",
    )
    assert create_response.status_code == 201
    card_id = create_response.json()["id"]

    monkeypatch.setattr(
        job_services,
        "_fetch_metadata",
        lambda url: {
            "title": "github.trending (@github.trending) on Threads",
            "description": "ExtractCSS라는 크롬 익스텐션으로 Tailwind 코드를 추출하는 사용법 소개",
            "og:title": "",
            "og:description": "바이브 디자인을 위한 툴 소개와 사용법",
            "og:image": "",
            "article_text": "",
            "article_excerpt": "",
        },
    )
    monkeypatch.setattr(
        job_services,
        "generate_summary_details",
        lambda **kwargs: SummaryResult(
            title="바이브 디자인을 위한 툴_ ExtractCSS라는 크롬 익스텐션",
            summary="Tailwind 추출을 빠르게 수행하는 도구 소개",
            details="익스텐션을 켜고 요소를 클릭하면 Tailwind 코드를 추출할 수 있다.",
            tags=["ExtractCSS", "Tailwind", "Chrome Extension"],
        ),
    )
    monkeypatch.setattr(job_services, "classify_folder_from_content", lambda **kwargs: None)

    job = Job.objects.get(job_type="fetch_metadata", target_id=card_id)
    job_services._handle_metadata_job(job)

    detail_response = client.get(f"/api/cards/{card_id}/")

    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["title"] == "바이브 디자인을 위한 툴_ ExtractCSS라는 크롬 익스텐션"
    assert payload["summary"] == "Tailwind 추출을 빠르게 수행하는 도구 소개"


@pytest.mark.django_db
def test_metadata_job_auto_generates_tags_when_ai_summary_returns_no_tags(monkeypatch):
    card = Card.objects.create(
        folder=Folder.objects.get(slug="uncategorized"),
        url="https://example.com/no-tags",
        normalized_url="https://example.com/no-tags",
        source_domain="example.com",
        title="example.com 문서",
    )

    monkeypatch.setattr(
        job_services,
        "_fetch_metadata",
        lambda url: {
            "title": "Example title",
            "description": "description",
            "og:title": "",
            "og:description": "",
            "og:image": "",
            "article_text": "Detailed coding article about React hooks and dependency management.",
            "article_excerpt": "React hooks dependency guide",
        },
    )
    monkeypatch.setattr(
        job_services,
        "generate_summary_details",
        lambda **kwargs: SummaryResult(
            title="리액트 훅 의존성 관리 가이드",
            summary="리액트 훅과 의존성 배열 설명",
            details="useEffect와 의존성 배열, cleanup, 재실행 조건을 설명한다.",
            tags=[],
        ),
    )
    monkeypatch.setattr(
        job_services,
        "generate_tags_from_text",
        lambda **kwargs: ["react", "hooks", "useEffect", "dependencies"],
    )
    monkeypatch.setattr(job_services, "classify_folder_from_content", lambda **kwargs: "coding")

    job = Job.objects.create(
        job_type="fetch_metadata",
        target_type="card",
        target_id=card.id,
        scheduled_at=timezone.now(),
        payload_json={"card_id": card.id},
    )

    job_services._handle_metadata_job(job)

    card.refresh_from_db()
    assert set(card.tags.values_list("name", flat=True)) == {"react", "hooks", "useEffect", "dependencies"}


@pytest.mark.django_db
def test_fetch_metadata_uses_threads_rendered_fallback_when_static_article_empty(monkeypatch):
    static_html = """
    <html>
      <head>
        <title>Static only</title>
        <meta property="og:description" content="static description" />
      </head>
      <body>
        <div>no article text</div>
      </body>
    </html>
    """
    rendered_html = """
    <html>
      <head><title>Rendered title</title></head>
      <body>
        <article>
          <p>
            This rendered paragraph has enough characters to pass minimum length and should be captured.
          </p>
        </article>
      </body>
    </html>
    """

    class _DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, _size):
            return static_html.encode("utf-8")

    monkeypatch.setattr(job_services, "urlopen", lambda request, timeout=10: _DummyResponse())
    monkeypatch.setattr(job_services, "_fetch_rendered_html", lambda url: rendered_html)

    metadata = job_services._fetch_metadata("https://www.threads.com/@test/post/abc")

    assert "should be captured" in metadata["article_text"]
    assert metadata["article_excerpt"]


@pytest.mark.django_db
def test_fetch_metadata_does_not_use_rendered_fallback_for_non_threads(monkeypatch):
    static_html = """
    <html>
      <head><title>Example</title></head>
      <body><article><p>Normal article content that is definitely longer than forty characters.</p></article></body>
    </html>
    """

    class _DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, _size):
            return static_html.encode("utf-8")

    monkeypatch.setattr(job_services, "urlopen", lambda request, timeout=10: _DummyResponse())
    monkeypatch.setattr(
        job_services,
        "_fetch_rendered_html",
        lambda url: (_ for _ in ()).throw(AssertionError("rendered fallback should not be called")),
    )

    metadata = job_services._fetch_metadata("https://example.com/post/1")

    assert "Normal article content" in metadata["article_text"]
