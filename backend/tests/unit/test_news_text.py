import datetime

from app.schemas.news import NewsItem
from app.services.news_text import (
    as_of_moment,
    drop_near_duplicates,
    format_brief,
    normalize_title,
    titles_are_near_duplicate,
)

AS_OF = datetime.datetime(2026, 7, 15, 10, 0, tzinfo=datetime.UTC)


def _item(title: str, hour: int, summary: str | None = "Sales rose.") -> NewsItem:
    return NewsItem(
        published_at=AS_OF.replace(hour=hour),
        source="Les Echos",
        title=title,
        summary=summary,
        url=f"https://example.com/{hour}",
    )


def test_punctuation_does_not_create_a_new_title() -> None:
    assert normalize_title("LVMH beats forecasts!") == normalize_title("LVMH beats forecasts")
    assert titles_are_near_duplicate("LVMH beats forecasts!", "LVMH beats forecasts")


def test_near_duplicates_keep_the_newest() -> None:
    older = _item("LVMH beats forecasts", 8)
    newer = _item("LVMH beats forecasts!", 11)

    kept = drop_near_duplicates([older, newer])

    assert [item.url for item in kept] == [newer.url]


def test_distinct_headlines_are_all_kept() -> None:
    first = _item("LVMH beats forecasts", 9)
    second = _item("Airbus lands a large order", 10)

    assert len(drop_near_duplicates([first, second])) == 2


def test_as_of_datetime_is_the_cutoff_instant() -> None:
    assert as_of_moment(AS_OF) == AS_OF


def test_as_of_date_includes_the_whole_utc_day() -> None:
    moment = as_of_moment(datetime.date(2026, 7, 15))
    assert moment.date() == datetime.date(2026, 7, 15)
    assert moment.hour == 23


def test_brief_truncates_a_long_summary() -> None:
    long = "x" * 400
    line = format_brief(_item("LVMH beats forecasts", 10, long))
    assert line.startswith("2026-07-15 · Les Echos · LVMH beats forecasts — ")
    assert line.endswith("…")
    assert len(line) < 400
