import datetime
import re

from app.agents.sentiment_analyst import report
from app.llm import FakeLLM
from app.schemas.agents import AnalystReport
from app.schemas.news import NewsItem

_AS_OF = datetime.date(2026, 7, 15)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _report() -> AnalystReport:
    return AnalystReport(
        stance="BEARISH",
        confidence=0.7,
        rationale="Lawsuit headline dominates the recent window.",
    )


def _headline(day: datetime.date, title: str = "LVMH faces a lawsuit") -> NewsItem:
    return NewsItem(
        published_at=datetime.datetime.combine(day, datetime.time(8, 0), tzinfo=datetime.UTC),
        source="Les Echos",
        title=title,
        summary="Court filing.",
        url=f"https://example.com/{day.isoformat()}",
    )


def test_report_returns_the_fake_llm_opinion() -> None:
    expected = _report()
    llm = FakeLLM([expected])

    assert report(llm, [_headline(_AS_OF)], _AS_OF) == expected


def test_no_headlines_is_neutral_without_calling_the_llm() -> None:
    llm = FakeLLM([_report()])

    result = report(llm, [], _AS_OF)

    assert result.stance == "NEUTRAL"
    assert result.confidence == 0.2
    assert llm.prompts == []


def test_user_prompt_has_no_date_after_as_of() -> None:
    llm = FakeLLM([_report()])
    report(llm, [_headline(_AS_OF), _headline(datetime.date(2026, 7, 10))], _AS_OF)
    _schema, _system, user = llm.prompts[0]

    found = [datetime.date.fromisoformat(match) for match in _ISO_DATE.findall(user)]
    assert found
    assert all(day <= _AS_OF for day in found)
    assert datetime.date(2026, 7, 16) not in found
