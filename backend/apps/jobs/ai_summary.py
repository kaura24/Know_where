from __future__ import annotations

import json
from dataclasses import dataclass

from django.conf import settings


@dataclass
class SummaryResult:
    title: str
    summary: str
    details: str
    tags: list[str]


def _build_client():
    try:
        from openai import OpenAI
    except ImportError:
        return None

    return OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_SECONDS,
        base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
    )


def generate_tags_from_text(*, title: str, url: str, text: str, max_tags: int = 7) -> list[str]:
    if not settings.AI_SUMMARY_ENABLED or not settings.OPENAI_API_KEY:
        return []

    source_text = text.strip()
    if not source_text:
        return []

    client = _build_client()
    if client is None:
        return []

    response = client.responses.create(
        model=settings.OPENAI_MODEL_SUMMARY,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Extract concise topic tags for a saved knowledge card. "
                            "Return valid JSON with a single key named tags. "
                            f"tags must be an array of up to {max_tags} short Korean or English topic tags."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"Title: {title}\n"
                            f"URL: {url}\n\n"
                            "Details text:\n"
                            f"{source_text[:8000]}"
                        ),
                    }
                ],
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    payload = json.loads(response.output_text)
    raw_tags = payload.get("tags", [])
    if not isinstance(raw_tags, list):
        return []
    return [str(tag).strip() for tag in raw_tags if str(tag).strip()][:max_tags]


def classify_folder_from_content(*, title: str, url: str, summary: str, details: str, tags: list[str]) -> str | None:
    if not settings.AI_SUMMARY_ENABLED or not settings.OPENAI_API_KEY:
        return None

    source_text = "\n".join(filter(None, [title, summary, details, " ".join(tags)])).strip()
    if not source_text:
        return None

    client = _build_client()
    if client is None:
        return None

    response = client.responses.create(
        model=settings.OPENAI_MODEL_SUMMARY,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Classify a saved knowledge card into exactly one folder. "
                            "Return valid JSON with a single key named folder_slug. "
                            "Allowed values are only: coding, travel, work, uncategorized. "
                            "If the content is about programming, technical stack, APIs, frameworks, tools, coding workflows, software usage, websites for developers, or skill usage in software, choose coding."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"URL: {url}\n"
                            f"Title: {title}\n"
                            f"Tags: {', '.join(tags)}\n\n"
                            f"Summary:\n{summary}\n\n"
                            f"Details:\n{details[:8000]}"
                        ),
                    }
                ],
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    payload = json.loads(response.output_text)
    folder_slug = str(payload.get("folder_slug", "")).strip().lower()
    if folder_slug in {"coding", "travel", "work", "uncategorized"}:
        return folder_slug
    return None


def generate_summary_details(
    *,
    title: str,
    url: str,
    article_text: str,
    article_excerpt: str,
    description: str = "",
    og_description: str = "",
) -> SummaryResult | None:
    if not settings.AI_SUMMARY_ENABLED or not settings.OPENAI_API_KEY:
        return None

    source_text = "\n\n".join(
        value.strip()
        for value in [article_text, article_excerpt, og_description, description]
        if value and value.strip()
    ).strip()
    if not source_text:
        return None

    client = _build_client()
    if client is None:
        return None

    response = client.responses.create(
        model=settings.OPENAI_MODEL_SUMMARY,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You write concise Korean knowledge cards. "
                            "Return valid JSON with keys title, summary, details, and tags. "
                            "title must be a direct Korean title created from the source content. "
                            "If the content is about coding, a technical stack, a program workflow, a tool usage pattern, a skill usage method, or a website usage guide, "
                            "the title must prioritize the concrete technology, product, framework, feature, or usage topic rather than a generic article title. "
                            "Prefer titles in the form '핵심 주제_핵심 도구/대상' when that structure makes the topic clearer. "
                            "Example: '바이브 디자인을 위한 툴_ ExtractCSS라는 크롬 익스텐션'. "
                            "Avoid vague titles and prefer specific technical nouns and task-oriented phrasing. "
                            "summary must be 2-3 Korean sentences. "
                            "details must be a structured Korean explanation in plain text with short paragraphs or bullet-like lines. "
                            "tags must be an array of up to 10 short Korean or English topic tags."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"Title: {title}\n"
                            f"URL: {url}\n\n"
                            f"Meta description: {description}\n"
                            f"OG description: {og_description}\n\n"
                            "Source text:\n"
                            f"{source_text[:12000]}\n\n"
                            "Write Korean title, summary, details, and tags for this card."
                        ),
                    }
                ],
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    payload = json.loads(response.output_text)
    title = str(payload.get("title", "")).strip()
    summary = str(payload.get("summary", "")).strip()
    details = str(payload.get("details", "")).strip()
    raw_tags = payload.get("tags", [])
    tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()][:10] if isinstance(raw_tags, list) else []

    if not title and not summary and not details and not tags:
        return None
    return SummaryResult(title=title, summary=summary, details=details, tags=tags)
