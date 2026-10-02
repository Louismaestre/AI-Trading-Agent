import datetime
import urllib.error
import urllib.request
from decimal import Decimal

import pytest

from app.agents.debate import argue_bear, argue_bull, format_transcript
from app.config import get_settings
from app.llm import FakeLLM, OllamaLLM
from app.schemas.agents import AnalystReport, DebateArgument, TechnicalSummary

_AS_OF = datetime.date(2026, 9, 15)


def _summary() -> TechnicalSummary:
    return TechnicalSummary(last_date=_AS_OF, last_close=Decimal("610"))


def _ollama_is_up() -> bool:
    url = get_settings().ollama_base_url.rstrip("/") + "/api/tags"
    try:
        urllib.request.urlopen(url, timeout=2)
    except (urllib.error.URLError, TimeoutError):
        return False
    return True


def test_format_transcript_is_none_when_empty() -> None:
    assert format_transcript([]) == "none"


def test_format_transcript_lists_sides() -> None:
    text = format_transcript(
        [
            DebateArgument(side="BULL", conviction=0.8, argument="up"),
            DebateArgument(side="BEAR", conviction=0.6, argument="down"),
        ]
    )
    assert text == "BULL: up\nBEAR: down"


def test_argue_bull_forces_bull_side() -> None:
    llm = FakeLLM([DebateArgument(side="BEAR", conviction=0.9, argument="actually down")])
    result = argue_bull(llm, _summary(), as_of=_AS_OF)
    assert result.side == "BULL"
    assert result.argument == "actually down"


def test_argue_bear_sees_reports_and_prior_turn() -> None:
    llm = FakeLLM([DebateArgument(side="BEAR", conviction=0.5, argument="reply")])
    reports = {"fundamental": AnalystReport(stance="BULLISH", confidence=0.7, rationale="margin")}
    prior = [DebateArgument(side="BULL", conviction=0.8, argument="margin expanded")]

    result = argue_bear(llm, _summary(), reports, transcript=prior, as_of=_AS_OF)

    assert result.side == "BEAR"
    user = llm.prompts[0][2]
    assert "margin" in user
    assert "margin expanded" in user
    assert str(_AS_OF) in user


@pytest.mark.llm
def test_ollama_bear_answers_the_bull() -> None:
    if not _ollama_is_up():
        pytest.skip("Ollama is not running")

    prior = [DebateArgument(side="BULL", conviction=0.8, argument="RSI 28 is oversold")]
    result = argue_bear(OllamaLLM(), _summary(), transcript=prior, as_of=_AS_OF)
    text = result.argument.lower()
    assert result.side == "BEAR"
    assert any(word in text for word in ("rsi", "oversold", "28"))
