from decimal import Decimal

from app.agents.risk_manager import assess
from app.llm import FakeLLM
from app.schemas.agents import AnalystDecision, AnalystReport, DebateArgument, RiskAssessment
from app.services.risk_rules import RiskBook


def _decision() -> AnalystDecision:
    return AnalystDecision(
        action="BUY",
        confidence=0.8,
        target_weight=0.1,
        rationale="RSI oversold",
    )


def _book() -> RiskBook:
    return RiskBook(
        ticker="MC.PA",
        sector="Luxury",
        total_value=Decimal("100000"),
        cash=Decimal("100000"),
        positions=(),
        orders_today=0,
    )


def _assessment() -> RiskAssessment:
    return RiskAssessment(
        approved=False,
        action="HOLD",
        target_weight=0,
        reasons=["Book already concentrated in luxury."],
    )


def test_assess_returns_the_fake_llm_verdict() -> None:
    expected = _assessment()
    llm = FakeLLM([expected])

    assert assess(llm, _decision(), _book()) == expected


def test_user_prompt_includes_the_decision_and_book() -> None:
    llm = FakeLLM([_assessment()])
    assess(llm, _decision(), _book())
    user = llm.prompts[0][2]
    assert "0.1" in user
    assert "MC.PA" in user


def test_reports_and_debate_are_included_in_the_prompt() -> None:
    llm = FakeLLM([_assessment()])
    reports = {
        "fundamental": AnalystReport(stance="BULLISH", confidence=0.7, rationale="margin up"),
    }
    debate = [DebateArgument(side="BEAR", conviction=0.6, argument="valuation stretched")]

    assess(llm, _decision(), _book(), reports=reports, debate=debate)
    user = llm.prompts[0][2]

    assert "margin up" in user
    assert "valuation stretched" in user


def test_missing_reports_and_debate_are_sent_as_none() -> None:
    llm = FakeLLM([_assessment()])
    assess(llm, _decision(), _book())
    user = llm.prompts[0][2]
    assert "none" in user
