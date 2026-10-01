import datetime

from app.providers.news_provider import articles_from_gdelt, articles_from_rss

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item>
<title>LVMH beats forecasts</title>
<link>https://example.com/lvmh</link>
<pubDate>Wed, 15 Jul 2026 08:00:00 GMT</pubDate>
<description>Sales rose 8%.</description>
</item>
<item>
<title>Missing link</title>
<pubDate>Wed, 15 Jul 2026 09:00:00 GMT</pubDate>
</item>
</channel></rss>
"""


def test_rss_skips_incomplete_items() -> None:
    items = articles_from_rss(RSS)
    assert len(items) == 1
    assert items[0].title == "LVMH beats forecasts"
    assert items[0].source == "Yahoo Finance"
    assert items[0].published_at == datetime.datetime(2026, 7, 15, 8, 0, tzinfo=datetime.UTC)
    assert items[0].summary == "Sales rose 8%."


def test_empty_or_broken_rss_gives_nothing() -> None:
    assert articles_from_rss(None) == []
    assert articles_from_rss("<not xml") == []


def test_gdelt_maps_seendate_and_domain() -> None:
    items = articles_from_gdelt(
        {
            "articles": [
                {
                    "url": "https://example.com/gdelt",
                    "title": "LVMH",
                    "seendate": "20260715T080000Z",
                    "domain": "lesechos.fr",
                },
                {"title": "no url"},
            ]
        }
    )
    assert len(items) == 1
    assert items[0].source == "lesechos.fr"
    assert items[0].published_at == datetime.datetime(2026, 7, 15, 8, 0, tzinfo=datetime.UTC)


def test_empty_gdelt_gives_nothing() -> None:
    assert articles_from_gdelt(None) == []
    assert articles_from_gdelt({}) == []
