from decimal import Decimal
from unittest.mock import MagicMock

from app.agents.seller import execute
from app.llm import FakeLLM
from app.models import OrderSide
from app.schemas.agents import AnalystDecision, QuantityProposal
from app.services.portfolio_service import PositionView


def _decision(weight: float = 0.1) -> AnalystDecision:
    return AnalystDecision(action="SELL", confidence=0.7, target_weight=weight, rationale="exit")


def _position(quantity: int) -> PositionView:
    return PositionView(
        ticker="MC.PA",
        quantity=quantity,
        average_cost=Decimal("500"),
        market_price=Decimal("500"),
        value=Decimal(quantity) * Decimal("500"),
    )


def _tools(*, price: Decimal | None = Decimal("500"), position: PositionView | None) -> MagicMock:
    tools = MagicMock()
    tools.get_last_price.return_value = price
    tools.get_total_value.return_value = Decimal("100000")
    tools.get_position.return_value = position
    tools.place_order.return_value = MagicMock()
    return tools


def test_seller_sells_10_shares_to_reach_a_10_percent_weight() -> None:
    llm = FakeLLM([QuantityProposal(quantity=10, rationale="keep 20")])
    tools = _tools(position=_position(30))

    execute(llm, tools, "MC.PA", _decision())

    tools.place_order.assert_called_once_with("MC.PA", OrderSide.SELL, 10)


def test_seller_corrects_an_aberrant_llm_quantity() -> None:
    llm = FakeLLM([QuantityProposal(quantity=30, rationale="sell all")])
    tools = _tools(position=_position(30))

    execute(llm, tools, "MC.PA", _decision())

    tools.place_order.assert_called_once_with("MC.PA", OrderSide.SELL, 10)


def test_seller_exits_when_target_weight_is_zero() -> None:
    llm = FakeLLM([QuantityProposal(quantity=30, rationale="flat")])
    tools = _tools(position=_position(30))

    execute(llm, tools, "MC.PA", _decision(weight=0))

    tools.place_order.assert_called_once_with("MC.PA", OrderSide.SELL, 30)


def test_seller_skips_when_already_at_target() -> None:
    llm = FakeLLM([QuantityProposal(quantity=1, rationale="unused")])
    tools = _tools(position=_position(20))

    assert execute(llm, tools, "MC.PA", _decision()) is None
    tools.place_order.assert_not_called()
    assert llm.prompts == []


def test_seller_skips_when_flat() -> None:
    tools = _tools(position=None)

    assert execute(FakeLLM([]), tools, "MC.PA", _decision()) is None
    tools.place_order.assert_not_called()


def test_seller_skips_when_price_is_missing() -> None:
    tools = _tools(price=None, position=_position(30))

    assert execute(FakeLLM([]), tools, "MC.PA", _decision()) is None
    tools.place_order.assert_not_called()
