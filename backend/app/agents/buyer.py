import logging
from pathlib import Path

from app.agents.tools import AgentTools, enforce_quantity, target_buy_quantity
from app.llm import StructuredLLM
from app.models import Order, OrderSide
from app.schemas.agents import AnalystDecision, QuantityProposal

logger = logging.getLogger(__name__)
SYSTEM = (Path(__file__).resolve().parent / "prompts" / "buyer.md").read_text(encoding="utf-8")


def execute(
    llm: StructuredLLM,
    tools: AgentTools,
    ticker: str,
    decision: AnalystDecision,
) -> Order | None:
    """Propose a buy size, correct it in Python, then place the order."""
    price = tools.get_last_price(ticker)
    if price is None:
        return None

    cash = tools.get_cash()
    total_value = tools.get_total_value()
    position = tools.get_position(ticker)
    held = position.quantity if position is not None else 0
    desired = target_buy_quantity(total_value, price, decision.target_weight)
    to_buy = max(0, desired - held)
    if to_buy < 1:
        return None

    position_text = f"{position.ticker} x {position.quantity}" if position is not None else "none"
    user = f"""
    Price: {price}
    Cash: {cash}
    Total value: {total_value}
    Position: {position_text}
    Analyst target_weight: {decision.target_weight}
    """
    proposal = llm.generate(QuantityProposal, SYSTEM, user)
    check = enforce_quantity(proposal.quantity, to_buy)
    if check.corrected:
        logger.warning(
            "buyer quantity corrected from %s to %s for %s",
            check.proposed,
            check.accepted,
            ticker,
        )
    if check.accepted < 1:
        return None
    return tools.place_order(ticker, OrderSide.BUY, check.accepted)
