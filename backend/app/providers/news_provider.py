"""Headlines from Yahoo RSS and GDELT. Callers must still filter on `as_of`."""

import datetime
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as Et
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

from app.schemas.news import NewsItem
from app.universe import UNIVERSE

logger = logging.getLogger(__name__)

_TIMEOUT = 15
_HEADERS = {"User-Agent": "AI-Trading-Agent/0.1"}
_YAHOO_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=FR&lang=fr-FR"
_GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"


def fetch_news(ticker: str) -> list[NewsItem]:
    """Merge RSS and GDELT. Empty list if both sources fail."""
    query = _search_name(ticker)
    items = articles_from_rss(_read_text(_YAHOO_RSS.format(ticker=urllib.parse.quote(ticker))))
    items.extend(articles_from_gdelt(_read_json(_gdelt_url(query))))
    return items


def articles_from_rss(xml: str | None) -> list[NewsItem]:
    if not xml:
        return []
    try:
        root = Et.fromstring(xml)
    except Et.ParseError:
        return []
    found: list[NewsItem] = []
    for item in root.iter("item"):
        parsed = _rss_item(item)
        if parsed is not None:
            found.append(parsed)
    return found


def articles_from_gdelt(payload: dict[str, Any] | None) -> list[NewsItem]:
    if not payload:
        return []
    found: list[NewsItem] = []
    for raw in payload.get("articles", []):
        parsed = _gdelt_item(raw)
        if parsed is not None:
            found.append(parsed)
    return found


def _rss_item(node: Et.Element) -> NewsItem | None:
    title = _child_text(node, "title")
    link = _child_text(node, "link")
    pub = _child_text(node, "pubDate")
    if not title or not link or not pub:
        return None
    published = _parse_rfc822(pub)
    if published is None:
        return None
    return NewsItem(
        published_at=published,
        source="Yahoo Finance",
        title=unescape(title),
        summary=_clip(_child_text(node, "description")),
        url=link.strip(),
    )


def _gdelt_item(raw: dict[str, Any]) -> NewsItem | None:
    title = raw.get("title")
    url = raw.get("url")
    seen = raw.get("seendate")
    if not isinstance(title, str) or not isinstance(url, str) or not isinstance(seen, str):
        return None
    published = _parse_gdelt(seen)
    if published is None:
        return None
    domain = raw.get("domain")
    source = domain if isinstance(domain, str) and domain else "GDELT"
    return NewsItem(
        published_at=published,
        source=source,
        title=unescape(title),
        summary=None,
        url=url.strip(),
    )


def _search_name(ticker: str) -> str:
    for entry in UNIVERSE:
        if entry.ticker == ticker:
            return entry.name
    return ticker


def _gdelt_url(query: str) -> str:
    params = urllib.parse.urlencode(
        {
            "query": f'"{query}"',
            "mode": "ArtList",
            "maxrecords": 25,
            "format": "json",
            "timespan": "7d",
        }
    )
    return f"{_GDELT}?{params}"


def _read_text(url: str) -> str | None:
    try:
        request = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
            body: bytes = response.read()
            return body.decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("news fetch failed for %s: %s", url, exc)
        return None


def _read_json(url: str) -> dict[str, Any] | None:
    text = _read_text(url)
    if not text:
        return None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return None
    return raw if isinstance(raw, dict) else None


def _child_text(node: Et.Element, tag: str) -> str | None:
    child = node.find(tag)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def _clip(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = unescape(" ".join(text.split()))
    return cleaned[:2000] or None


def _parse_rfc822(value: str) -> datetime.datetime | None:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.UTC)
    return parsed.astimezone(datetime.UTC)


def _parse_gdelt(value: str) -> datetime.datetime | None:
    try:
        return datetime.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime.UTC)
    except ValueError:
        return None
