"""Title cleanup, near-duplicate drop, and compact lines for agent prompts."""

import datetime
import re
from collections.abc import Sequence
from difflib import SequenceMatcher

from app.market_clock import ensure_aware
from app.schemas.news import NewsItem

SUMMARY_LIMIT = 280
NEAR_DUPLICATE = 0.88

_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)


def normalize_title(title: str) -> str:
    return " ".join(_PUNCT.sub(" ", title.lower()).split())


def titles_are_near_duplicate(left: str, right: str, threshold: float = NEAR_DUPLICATE) -> bool:
    a, b = normalize_title(left), normalize_title(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return SequenceMatcher(None, a, b).ratio() >= threshold


def drop_near_duplicates(items: Sequence[NewsItem]) -> list[NewsItem]:
    """Keep the newest of each near-duplicate cluster. Input need not be sorted."""
    newest_first = sorted(items, key=lambda item: item.published_at, reverse=True)
    kept: list[NewsItem] = []
    for item in newest_first:
        if any(titles_are_near_duplicate(item.title, seen.title) for seen in kept):
            continue
        kept.append(item)
    return kept


def as_of_moment(as_of: datetime.date | datetime.datetime) -> datetime.datetime:
    """Latest instant still visible at `as_of`. A bare date includes that whole UTC day."""
    if isinstance(as_of, datetime.datetime):
        return ensure_aware(as_of)
    return datetime.datetime.combine(as_of, datetime.time(23, 59, 59), tzinfo=datetime.UTC)


def format_brief(item: NewsItem) -> str:
    summary = (item.summary or "").strip()
    if len(summary) > SUMMARY_LIMIT:
        summary = summary[: SUMMARY_LIMIT - 1] + "…"
    line = f"{item.published_at.date().isoformat()} · {item.source} · {item.title}"
    if summary:
        return f"{line} — {summary}"
    return line
