import datetime
import re
from decimal import Decimal

from app.agents.fundamental_analyst import report
from app.llm import FakeLLM
from app.schemas.agents import AnalystReport
from app.schemas.fundamentals import FundamentalPeriod, FundamentalSnapshot

_AS_OF = datetime.date(2026, 7, 15)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _report() -> AnalystReport:
    return AnalystReport(
        stance="BULLISH",
        confidence=0.6,
        rationale="Margin and revenue growth look solid versus the given PE.",
    )


def _snapshot(*period_ends: datetime.date) -> FundamentalSnapshot:
    return FundamentalSnapshot(
        as_of=_AS_OF,
        price=Decimal("100"),
        statements=[
            FundamentalPeriod(period_end=day, revenue=Decimal("1000"), net_income=Decimal("100"))
            for day in period_ends
        ],
        pe_ratio=Decimal("10"),
        revenue_growth=Decimal("0.2"),
        net_margin=Decimal("0.1"),
        leverage=Decimal("0.5"),
    )


def test_report_returns_the_fake_llm_opinion() -> None:
    expected = _report()
    llm = FakeLLM([expected])

    assert report(llm, _snapshot(datetime.date(2026, 3, 31))) == expected


def test_empty_snapshot_is_neutral_without_calling_the_llm() -> None:
    llm = FakeLLM([_report()])

    result = report(llm, _snapshot())

    assert result.stance == "NEUTRAL"
    assert result.confidence == 0.2
    assert llm.prompts == []


def test_user_prompt_has_no_date_after_as_of() -> None:
    llm = FakeLLM([_report()])
    report(llm, _snapshot(datetime.date(2026, 3, 31)))
    _schema, _system, user = llm.prompts[0]

    found = [datetime.date.fromisoformat(match) for match in _ISO_DATE.findall(user)]
    assert found
    assert all(day <= _AS_OF for day in found)
    assert datetime.date(2026, 6, 30) not in found
