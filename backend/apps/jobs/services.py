from __future__ import annotations

import contextlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from apps.cards.models import Card
from .ai_summary import classify_folder_from_content, generate_summary_details, generate_tags_from_text
from .models import Job


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._capture_title = False
        self.meta: dict[str, str] = {}
        self._container_stack: list[bool] = []
        self._capture_paragraph = False
        self._paragraph_buffer: list[str] = []
        self.article_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        attr_map = dict(attrs)
        if tag == "title":
            self._capture_title = True
        if tag == "meta":
            key = attr_map.get("property") or attr_map.get("name")
            content = attr_map.get("content")
            if key and content:
                self.meta[key.lower()] = content.strip()
        container_hint = " ".join(
            filter(
                None,
                [
                    attr_map.get("id", ""),
                    attr_map.get("class", ""),
                ],
            )
        ).lower()
        is_article_container = tag in {"article", "main"} or any(
            token in container_hint for token in ("article", "content", "view", "news", "body")
        )
        self._container_stack.append(is_article_container or (self._container_stack[-1] if self._container_stack else False))

        if tag == "p" and self._container_stack and self._container_stack[-1]:
            self._capture_paragraph = True
            self._paragraph_buffer = []

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._capture_title = False
        if tag == "p" and self._capture_paragraph:
            paragraph = " ".join(part.strip() for part in self._paragraph_buffer if part.strip()).strip()
            if len(paragraph) >= 40:
                self.article_chunks.append(paragraph)
            self._capture_paragraph = False
            self._paragraph_buffer = []
        if self._container_stack:
            self._container_stack.pop()

    def handle_data(self, data: str):
        if self._capture_title:
            self.title += data.strip()
        if self._capture_paragraph:
            self._paragraph_buffer.append(data)


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _parse_metadata_html(html: str) -> dict[str, str]:
    parser = _MetadataParser()
    parser.feed(html)
    article_text = "\n\n".join(parser.article_chunks).strip()
    normalized_article = _normalize_text(article_text)
    return {
        "title": parser.title.strip(),
        "description": parser.meta.get("description", ""),
        "og:title": parser.meta.get("og:title", ""),
        "og:description": parser.meta.get("og:description", ""),
        "og:image": parser.meta.get("og:image", ""),
        "article_text": article_text,
        "article_excerpt": normalized_article[:400],
    }


def _is_threads_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname == "threads.com" or hostname.endswith(".threads.com")


def _fetch_rendered_html(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.goto(url, wait_until="networkidle", timeout=30000)
            return page.content()
        finally:
            with contextlib.suppress(Exception):
                browser.close()


def enqueue_card_jobs(card: Card) -> None:
    now = timezone.now()
    Job.objects.get_or_create(
        job_type="fetch_metadata",
        target_type="card",
        target_id=card.id,
        defaults={"scheduled_at": now, "payload_json": {"card_id": card.id}},
    )
    Job.objects.get_or_create(
        job_type="generate_thumbnail",
        target_type="card",
        target_id=card.id,
        defaults={"scheduled_at": now, "payload_json": {"card_id": card.id}},
    )


def retry_card_jobs(card: Card) -> None:
    now = timezone.now()
    Job.objects.filter(target_type="card", target_id=card.id, job_type="fetch_metadata").update(
        status=Job.JobStatus.QUEUED,
        scheduled_at=now,
        started_at=None,
        finished_at=None,
        last_error=None,
    )
    Job.objects.filter(target_type="card", target_id=card.id, job_type="generate_thumbnail").update(
        status=Job.JobStatus.QUEUED,
        scheduled_at=now,
        started_at=None,
        finished_at=None,
        last_error=None,
    )
    card.ingestion_status = Card.ProcessingStatus.PENDING
    card.ingestion_error = None
    card.thumbnail_status = Card.ProcessingStatus.PENDING
    card.thumbnail_error = None
    card.save(
        update_fields=[
            "ingestion_status",
            "ingestion_error",
            "thumbnail_status",
            "thumbnail_error",
            "updated_at",
        ]
    )


def process_jobs(limit: int = 20) -> int:
    processed = 0
    jobs = (
        Job.objects.filter(status=Job.JobStatus.QUEUED, scheduled_at__lte=timezone.now())
        .order_by("priority", "scheduled_at", "id")[:limit]
    )
    for job in jobs:
        _process_single_job(job)
        processed += 1
    return processed


def _process_single_job(job: Job) -> None:
    job.status = Job.JobStatus.PROCESSING
    job.attempt_count += 1
    job.started_at = timezone.now()
    job.last_error = None
    job.save(update_fields=["status", "attempt_count", "started_at", "last_error"])

    try:
        if job.job_type == "fetch_metadata":
            _handle_metadata_job(job)
        elif job.job_type == "generate_thumbnail":
            _handle_thumbnail_job(job)
        else:
            raise ValueError(f"Unsupported job type: {job.job_type}")
        job.status = Job.JobStatus.DONE
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "finished_at"])
    except Exception as exc:  # noqa: BLE001
        job.status = Job.JobStatus.FAILED
        job.last_error = str(exc)
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "last_error", "finished_at"])


def _handle_metadata_job(job: Job) -> None:
    card = Card.objects.get(id=job.target_id)
    card.ingestion_status = Card.ProcessingStatus.PROCESSING
    card.ingestion_error = None
    card.save(update_fields=["ingestion_status", "ingestion_error", "updated_at"])

    try:
        metadata = _fetch_metadata(card.url)
        article_text = metadata.get("article_text", "")
        article_excerpt = metadata.get("article_excerpt", "")
        title = metadata.get("og:title") or metadata.get("title") or card.title
        fallback_summary = (
            metadata.get("og:description")
            or metadata.get("description")
            or article_excerpt
            or card.summary
        )
        fallback_details = (
            article_text
            or article_excerpt
            or metadata.get("og:description")
            or metadata.get("description")
            or card.details
            or ""
        )
        ai_result = generate_summary_details(
            title=title,
            url=card.url,
            article_text=article_text,
            article_excerpt=article_excerpt,
            description=metadata.get("description", ""),
            og_description=metadata.get("og:description", ""),
        )
        title = ai_result.title if ai_result and ai_result.title else title
        summary = ai_result.summary if ai_result and ai_result.summary else fallback_summary
        details = ai_result.details if ai_result and ai_result.details else fallback_details
        card.title = title
        card.summary = summary
        card.details = details
        card.ingestion_status = Card.ProcessingStatus.READY
        card.ingestion_error = None
        card.save(
            update_fields=[
                "title",
                "summary",
                "details",
                "ingestion_status",
                "ingestion_error",
                "updated_at",
            ]
        )
        from apps.cards.services import get_or_create_default_folder, sync_tags

        auto_tags = ai_result.tags if ai_result and ai_result.tags else generate_tags_from_text(
            title=card.title,
            url=card.url,
            text=card.details or card.summary,
            max_tags=7,
        )
        if auto_tags:
            sync_tags(card, auto_tags)

        if card.folder.slug == "uncategorized":
            folder_slug = classify_folder_from_content(
                title=card.title,
                url=card.url,
                summary=card.summary,
                details=card.details,
                tags=auto_tags,
            )
            if folder_slug and folder_slug != card.folder.slug:
                card.folder = get_or_create_default_folder(folder_slug)
                card.save(update_fields=["folder", "updated_at"])
    except Exception as exc:  # noqa: BLE001
        card.ingestion_status = Card.ProcessingStatus.FAILED
        card.ingestion_error = str(exc)
        card.save(update_fields=["ingestion_status", "ingestion_error", "updated_at"])
        raise


def _fetch_metadata(url: str) -> dict[str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; KnowWhereBot/0.1)",
        },
    )
    with urlopen(request, timeout=10) as response:
        html = response.read(1024 * 1024).decode("utf-8", errors="ignore")

    metadata = _parse_metadata_html(html)
    if _is_threads_url(url) and not _normalize_text(metadata.get("article_text", "")):
        with contextlib.suppress(Exception):
            rendered_html = _fetch_rendered_html(url)
            rendered_metadata = _parse_metadata_html(rendered_html)
            if _normalize_text(rendered_metadata.get("article_text", "")):
                metadata["article_text"] = rendered_metadata["article_text"]
                metadata["article_excerpt"] = rendered_metadata["article_excerpt"]
            for key in ("title", "description", "og:title", "og:description", "og:image"):
                if not metadata.get(key) and rendered_metadata.get(key):
                    metadata[key] = rendered_metadata[key]
    return metadata


def _handle_thumbnail_job(job: Job) -> None:
    card = Card.objects.get(id=job.target_id)
    card.thumbnail_status = Card.ProcessingStatus.PROCESSING
    card.thumbnail_error = None
    card.save(update_fields=["thumbnail_status", "thumbnail_error", "updated_at"])

    try:
        path = _capture_thumbnail(card)
        card.thumbnail_status = Card.ProcessingStatus.READY
        card.thumbnail_path = path
        card.thumbnail_error = None
        card.save(update_fields=["thumbnail_status", "thumbnail_path", "thumbnail_error", "updated_at"])
    except Exception as exc:  # noqa: BLE001
        card.thumbnail_status = Card.ProcessingStatus.FAILED
        card.thumbnail_error = str(exc)
        card.save(update_fields=["thumbnail_status", "thumbnail_error", "updated_at"])
        raise


def _capture_thumbnail(card: Card) -> str:
    from playwright.sync_api import sync_playwright

    timestamp = timezone.now()
    relative_path = Path("thumbnails") / f"{timestamp.year:04d}" / f"{timestamp.month:02d}" / f"{card.id}.png"
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(card.url, wait_until="networkidle", timeout=15000)
            page.screenshot(path=str(absolute_path), full_page=False)
        finally:
            with contextlib.suppress(Exception):
                browser.close()

    return f"{settings.MEDIA_URL}{relative_path.as_posix()}"
