from urllib.parse import urlparse

from django.utils.text import slugify

from apps.folders.models import Folder
from apps.jobs.services import enqueue_card_jobs
from .models import Card, Tag


AUTO_FOLDER_RULES = {
    "coding": {
        "domains": {
            "github.com",
            "gitlab.com",
            "stackoverflow.com",
            "react.dev",
            "developer.mozilla.org",
            "docs.python.org",
            "pypi.org",
            "npmjs.com",
        },
        "keywords": {
            "code",
            "coding",
            "python",
            "javascript",
            "typescript",
            "react",
            "django",
            "api",
            "programming",
            "개발",
            "코딩",
            "프론트엔드",
            "백엔드",
            "알고리즘",
            "라이브러리",
        },
    },
    "travel": {
        "domains": {
            "tripadvisor.com",
            "airbnb.com",
            "booking.com",
            "agoda.com",
            "skyscanner.com",
            "klook.com",
        },
        "keywords": {
            "travel",
            "trip",
            "flight",
            "hotel",
            "tour",
            "itinerary",
            "vacation",
            "journey",
            "여행",
            "항공",
            "숙소",
            "호텔",
            "투어",
            "맛집",
            "일정",
            "관광",
        },
    },
    "work": {
        "domains": {
            "slack.com",
            "notion.so",
            "docs.google.com",
            "drive.google.com",
            "asana.com",
            "trello.com",
            "atlassian.com",
        },
        "keywords": {
            "work",
            "meeting",
            "project",
            "report",
            "proposal",
            "schedule",
            "business",
            "task",
            "업무",
            "회의",
            "보고서",
            "프로젝트",
            "기획",
            "협업",
            "일정",
        },
    },
}


def normalize_url(url: str) -> str:
    return url.strip()


def build_fallback_title(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or "untitled"
    return f"{domain} 문서"


def get_or_create_default_folder(slug: str) -> Folder:
    defaults = {
        "uncategorized": {"name": "미분류", "color": "gray", "sort_order": 0, "is_system": True},
        "coding": {"name": "코딩", "color": "blue", "sort_order": 10, "is_system": True},
        "travel": {"name": "여행", "color": "emerald", "sort_order": 20, "is_system": True},
        "work": {"name": "업무", "color": "amber", "sort_order": 30, "is_system": True},
    }
    folder, _ = Folder.objects.get_or_create(slug=slug, defaults=defaults[slug])
    return folder


def detect_auto_folder(url: str, title: str, memo: str, tag_names: list[str]) -> Folder | None:
    parsed = urlparse(url)
    domain = (parsed.netloc or "").lower()
    haystack = " ".join([url, title, memo, *tag_names]).lower()

    best_slug = None
    best_score = 0

    for slug, rule in AUTO_FOLDER_RULES.items():
        score = 0
        if domain in rule["domains"]:
            score += 4
        score += sum(1 for keyword in rule["keywords"] if keyword in haystack)
        if score > best_score:
            best_score = score
            best_slug = slug

    if not best_slug or best_score < 2:
        return None
    return get_or_create_default_folder(best_slug)


def sync_tags(card: Card, tag_names: list[str]) -> None:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in tag_names:
        name = raw.strip()
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        cleaned.append(name)

    tags = []
    for name in cleaned:
        tag, _ = Tag.objects.get_or_create(
            normalized_name=slugify(name, allow_unicode=True),
            defaults={"name": name},
        )
        if tag.name != name:
            tag.name = name
            tag.save(update_fields=["name"])
        tags.append(tag)

    card.tags.set(tags)
    card.tags_text = " ".join(tag.name for tag in tags)
    card.save(update_fields=["tags_text", "updated_at"])


def create_card(validated_data: dict) -> Card:
    tag_names = validated_data.pop("tags", [])
    folder_id = validated_data.pop("folder_id", None)
    url = validated_data["url"]
    normalized_url = normalize_url(url)
    title = validated_data.get("title") or build_fallback_title(normalized_url)
    memo = validated_data.get("memo", "")
    uncategorized = get_or_create_default_folder("uncategorized")
    folder = Folder.objects.filter(id=folder_id).first()
    if folder is None:
        folder = detect_auto_folder(normalized_url, title, memo, tag_names) or uncategorized

    card = Card.objects.create(
        folder=folder,
        url=url,
        normalized_url=normalized_url,
        source_domain=urlparse(normalized_url).netloc,
        title=title,
        summary=validated_data.get("summary", ""),
        details=validated_data.get("details", ""),
        memo=memo,
    )
    sync_tags(card, tag_names)
    enqueue_card_jobs(card)
    return card


def update_card(card: Card, validated_data: dict) -> Card:
    tag_names = validated_data.pop("tags", None)
    folder_id = validated_data.pop("folder_id", None)
    if folder_id is not None:
        card.folder_id = folder_id

    for field, value in validated_data.items():
        setattr(card, field, value)
    if validated_data or folder_id is not None:
        card.save()

    if tag_names is not None:
        sync_tags(card, tag_names)
    return card


def regenerate_card_tags(card: Card) -> Card:
    raise ValueError(
        "AI 태그 생성은 비활성화되었습니다. AI 처리는 신규 저장 또는 새로고침에서만 수행됩니다."
    )
