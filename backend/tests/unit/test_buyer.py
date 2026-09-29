from decimal import Decimal
from unittest.mock import MagicMock

from app.agents.buyer import execute
from app.llm import FakeLLM
from app.models import OrderSide
from app.schemas.agents import AnalystDecision, QuantityProposal
from app.services.portfolio_service import PositionView


def _decision() -> AnalystDecision:
    return AnalystDecision(action="BUY", confidence=0.7, target_weight=0.1, rationale="setup")


def _tools(
    *,
    price: Decimal = Decimal("500"),
    cash: Decimal = Decimal("100000"),
    total_value: Decimal = Decimal("100000"),
    position: PositionView | None = None,
) -> MagicMock:
    tools = MagicMock()
    tools.get_last_price.return_value = price
    tools.get_cash.return_value = cash
    tools.get_total_value.return_value = total_value
    tools.get_position.return_value = position
    tools.place_order.return_value = MagicMock()
    return tools


def test_buyer_places_20_shares_on_a_10_percent_100k_book() -> None:
    llm = FakeLLM([QuantityProposal(quantity=20, rationale="10 percent")])
    tools = _tools()

    execute(llm, tools, "MC.PA", _decision())

    tools.place_order.assert_called_once_with("MC.PA", OrderSide.BUY, 20)


def test_buyer_corrects_an_aberrant_llm_quantity() -> None:
    llm = FakeLLM([QuantityProposal(quantity=1000, rationale="too many")])
    tools = _tools()

    execute(llm, tools, "MC.PA", _decision())

    tools.place_order.assert_called_once_with("MC.PA", OrderSide.BUY, 20)


def test_buyer_only_buys_the_missing_shares() -> None:
    llm = FakeLLM([QuantityProposal(quantity=20, rationale="ignore held")])
    tools = _tools(
        position=PositionView(
            ticker="MC.PA",
            quantity=5,
            average_cost=Decimal("500"),
            market_price=Decimal("500"),
            value=Decimal("2500"),
        )
    )

    execute(llm, tools, "MC.PA", _decision())

    tools.place_order.assert_called_once_with("MC.PA", OrderSide.BUY, 15)


def test_buyer_skips_when_already_at_target() -> None:
    llm = FakeLLM([QuantityProposal(quantity=1, rationale="unused")])
    tools = _tools(
        position=PositionView(
            ticker="MC.PA",
            quantity=20,
            average_cost=Decimal("500"),
            market_price=Decimal("500"),
            value=Decimal("10000"),
        )
    )

    assert execute(llm, tools, "MC.PA", _decision()) is None
    tools.place_order.assert_not_called()
    assert llm.prompts == []


def test_buyer_skips_when_price_is_missing() -> None:
    tools = _tools()
    tools.get_last_price.return_value = None

    assert execute(FakeLLM([]), tools, "MC.PA", _decision()) is None
    tools.place_order.assert_not_called()
