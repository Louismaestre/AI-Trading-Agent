import datetime
from decimal import Decimal
from typing import Any, cast
from unittest.mock import MagicMock

from app.agents.graph import build_graph
from app.llm import FakeLLM
from app.models import OrderSide
from app.schemas.agents import AnalystDecision, QuantityProposal, TechnicalSummary
from app.services.portfolio_service import PositionView


def _summary() -> TechnicalSummary:
    return TechnicalSummary(last_date=datetime.date(2026, 9, 15), last_close=Decimal("500"))


def _state() -> dict[str, Any]:
    return {
        "ticker": "MC.PA",
        "as_of": datetime.date(2026, 9, 15),
        "summary": _summary(),
        "decision": None,
        "order": None,
    }


def _tools() -> MagicMock:
    tools = MagicMock()
    tools.get_position.return_value = None
    tools.get_last_price.return_value = Decimal("500")
    tools.get_cash.return_value = Decimal("100000")
    tools.get_total_value.return_value = Decimal("100000")
    tools.place_order.return_value = MagicMock()
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
