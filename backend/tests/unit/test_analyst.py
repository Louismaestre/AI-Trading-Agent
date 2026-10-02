import datetime
import re
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

from app.agents.analyst import decide
from app.config import get_settings
from app.llm import FakeLLM, OllamaLLM
from app.schemas.agents import AnalystDecision, PriorYearContext, TechnicalSummary
from app.schemas.portfolio import PositionResponse

_AS_OF = datetime.date(2026, 9, 15)
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _summary() -> TechnicalSummary:
    return TechnicalSummary(
        last_date=_AS_OF,
        last_close=Decimal("610.25"),
        sma_20=Decimal("600"),
        sma_50=Decimal("590"),
        rsi_14=Decimal("28"),
        signals=["price above SMA 20", "RSI oversold"],
    )


def _decision() -> AnalystDecision:
    return AnalystDecision(
        action="BUY",
        confidence=0.7,
        target_weight=0.1,
        rationale="RSI oversold and price above SMA 20.",
    )


def test_decide_returns_the_fake_llm_decision() -> None:
    expected = _decision()
    llm = FakeLLM([expected])

    assert decide(llm, _summary(), None, _AS_OF) == expected


def test_user_prompt_has_no_date_after_as_of() -> None:
    llm = FakeLLM([_decision()])
    decide(llm, _summary(), None, _AS_OF)
    _schema, _system, user = llm.prompts[0]

    found = [datetime.date.fromisoformat(match) for match in _ISO_DATE.findall(user)]
    assert found
    assert all(day <= _AS_OF for day in found)


def test_flat_position_is_sent_as_none() -> None:
    llm = FakeLLM([_decision()])
    decide(llm, _summary(), None, _AS_OF)
    assert "none" in llm.prompts[0][2]


def test_prior_year_context_is_included_in_the_prompt() -> None:
    llm = FakeLLM([_decision()])
    prior = PriorYearContext(
        year=2025,
        ticker="MC.PA",
        ticker_return=Decimal("0.12"),
        index_ticker="^FCHI",
        index_return=Decimal("0.08"),
    )
    decide(llm, _summary(), None, _AS_OF, prior_year=prior)
    user = llm.prompts[0][2]
    assert "0.12" in user
    assert "^FCHI" in user


def test_open_position_is_included_in_the_prompt() -> None:
    llm = FakeLLM([_decision()])
    position = PositionResponse(
        ticker="MC.PA",
        quantity=10,
        average_cost=Decimal("600"),
        market_price=Decimal("610.25"),
        value=Decimal("6102.50"),
    )
    decide(llm, _summary(), position, _AS_OF)
    assert "MC.PA" in llm.prompts[0][2]


def _ollama_is_up() -> bool:
    url = get_settings().ollama_base_url.rstrip("/") + "/api/tags"
    try:
        urllib.request.urlopen(url, timeout=2)
    except (urllib.error.URLError, TimeoutError):
        return False
    return True


@pytest.mark.llm
def test_ollama_rationale_cites_provided_indicators() -> None:
    if not _ollama_is_up():
        pytest.skip("Ollama is not running")

    decision = decide(OllamaLLM(), _summary(), None, _AS_OF)
    text = decision.rationale.lower()
    assert any(word in text for word in ("rsi", "sma", "oversold"))
