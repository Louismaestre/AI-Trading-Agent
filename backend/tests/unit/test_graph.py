import datetime
from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock

from app.agents.graph import GraphConfig, build_graph
from app.llm import FakeLLM
from app.models import OrderSide
from app.schemas.agents import (
    AnalystDecision,
    DebateArgument,
    QuantityProposal,
    RiskAssessment,
    TechnicalSummary,
)
from app.services.portfolio_service import PositionView
from app.services.risk_rules import RiskBook


def _summary() -> TechnicalSummary:
    return TechnicalSummary(last_date=datetime.date(2026, 9, 15), last_close=Decimal("500"))


def _state() -> dict[str, Any]:
    return {
        "ticker": "MC.PA",
        "as_of": datetime.date(2026, 9, 15),
        "summary": _summary(),
        "decision": None,
        "order": None,
        "reports": {},
        "debate": [],
        "risk": None,
    }


def _tools() -> MagicMock:
    tools = MagicMock()
    tools.get_position.return_value = None
    tools.get_last_price.return_value = Decimal("500")
    tools.get_cash.return_value = Decimal("100000")
    tools.get_total_value.return_value = Decimal("100000")
    tools.place_order.return_value = MagicMock()
    tools.get_fundamentals.return_value = None
    tools.get_news.return_value = []
    tools.get_prior_year_context.return_value = None
    tools.get_risk_book.return_value = RiskBook(
        ticker="MC.PA",
        sector="Luxury",
        total_value=Decimal("100000"),
        cash=Decimal("100000"),
        positions=(),
        orders_today=0,
    )
    return tools


def _run(llm: FakeLLM, tools: MagicMock) -> dict[str, Any]:
    graph = cast(Any, build_graph(llm, tools))
    return graph.invoke(_state())


def test_hold_stops_without_placing_an_order() -> None:
    llm = FakeLLM(
        [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
    )
    tools = _tools()

    result = _run(llm, tools)

    assert result["decision"].action == "HOLD"
    assert result["order"] is None
    tools.place_order.assert_not_called()


def test_buy_routes_to_the_buyer() -> None:
    llm = FakeLLM(
        [
            AnalystDecision(action="BUY", confidence=0.7, target_weight=0.1, rationale="setup"),
            QuantityProposal(quantity=20, rationale="10 percent"),
        ]
    )
    tools = _tools()

    result = _run(llm, tools)

    assert result["decision"].action == "BUY"
    tools.place_order.assert_called_once_with("MC.PA", OrderSide.BUY, 20)


def test_sell_routes_to_the_seller() -> None:
    llm = FakeLLM(
        [
            AnalystDecision(action="SELL", confidence=0.7, target_weight=0, rationale="exit"),
            QuantityProposal(quantity=10, rationale="flat"),
        ]
    )
    tools = _tools()
    tools.get_position.return_value = PositionView(
        ticker="MC.PA",
        quantity=10,
        average_cost=Decimal("500"),
        market_price=Decimal("500"),
        value=Decimal("5000"),
    )

    result = _run(llm, tools)

    assert result["decision"].action == "SELL"
    tools.place_order.assert_called_once_with("MC.PA", OrderSide.SELL, 10)


def test_specialists_read_fundamentals_and_news() -> None:
    llm = FakeLLM(
        [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
    )
    tools = _tools()

    result = _run(llm, tools)

    tools.get_fundamentals.assert_called_once_with("MC.PA")
    tools.get_news.assert_called_once_with("MC.PA")
    assert result["debate"] == []


def test_zero_rounds_skips_researchers() -> None:
    llm = FakeLLM(
        [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
    )

    result = _run(llm, _tools())

    assert result["debate"] == []
    assert [schema.__name__ for schema, _system, _user in llm.prompts] == ["AnalystDecision"]


def test_two_rounds_produce_four_alternating_arguments() -> None:
    llm = FakeLLM(
        [
            DebateArgument(side="BULL", conviction=0.8, argument="up 1"),
            DebateArgument(side="BEAR", conviction=0.7, argument="valuation stretched"),
            DebateArgument(side="BULL", conviction=0.6, argument="up 2"),
            DebateArgument(side="BEAR", conviction=0.5, argument="down 2"),
            AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait"),
        ]
    )
    graph = cast(Any, build_graph(llm, _tools(), GraphConfig(debate_rounds=2)))

    result = graph.invoke(_state())

    assert [item.side for item in result["debate"]] == ["BULL", "BEAR", "BULL", "BEAR"]
    assert len(result["debate"]) == 4
    bull_turns = [user for schema, _system, user in llm.prompts if schema is DebateArgument]
    assert "valuation stretched" in bull_turns[2]


def test_risk_refusal_blocks_the_order() -> None:
    llm = FakeLLM(
        [
            AnalystDecision(action="BUY", confidence=0.8, target_weight=0.1, rationale="setup"),
            RiskAssessment(approved=False, action="HOLD", target_weight=0, reasons=["crowded"]),
        ]
    )
    tools = _tools()
    graph = cast(Any, build_graph(llm, tools, GraphConfig(risk=True)))

    result = graph.invoke(_state())

    assert result["decision"].action == "HOLD"
    assert result["risk"].approved is False
    tools.place_order.assert_not_called()


def test_risk_cannot_raise_the_analyst_weight() -> None:
    llm = FakeLLM(
        [
            AnalystDecision(action="BUY", confidence=0.8, target_weight=0.1, rationale="setup"),
            RiskAssessment(approved=True, action="BUY", target_weight=0.5, reasons=["fine"]),
            QuantityProposal(quantity=20, rationale="10 percent"),
        ]
    )
    tools = _tools()
    graph = cast(Any, build_graph(llm, tools, GraphConfig(risk=True)))

    result = graph.invoke(_state())

    assert result["decision"].target_weight == 0.1
    assert result["risk"].target_weight == 0.1
    tools.place_order.assert_called_once_with("MC.PA", OrderSide.BUY, 20)


def test_risk_off_skips_the_risk_manager() -> None:
    llm = FakeLLM(
        [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
    )

    _run(llm, _tools())

    assert [schema.__name__ for schema, _system, _user in llm.prompts] == ["AnalystDecision"]
