import logging
from pathlib import Path

from app.agents.tools import AgentTools, enforce_quantity, target_sell_quantity
from app.llm import StructuredLLM
from app.models import Order, OrderSide
from app.schemas.agents import AnalystDecision, QuantityProposal

logger = logging.getLogger(__name__)
SYSTEM = (Path(__file__).resolve().parent / "prompts" / "seller.md").read_text(encoding="utf-8")


def execute(
    llm: StructuredLLM,
    tools: AgentTools,
    ticker: str,
    decision: AnalystDecision,
) -> Order | None:
    """Propose a sell size, correct it in Python, then place the order."""
    price = tools.get_last_price(ticker)
    if price is None:
        return None

    total_value = tools.get_total_value()
    position = tools.get_position(ticker)
    if position is None:
        return None
    to_sell = target_sell_quantity(position.quantity, total_value, price, decision.target_weight)
    if to_sell < 1:
        return None

    position_text = f"{position.ticker} x {position.quantity}"
    user = f"""
    Price: {price}
    Total value: {total_value}
    Position: {position_text}
    Analyst target_weight: {decision.target_weight}
    """
    proposal = llm.generate(QuantityProposal, SYSTEM, user)
    check = enforce_quantity(proposal.quantity, to_sell)
    if check.corrected:
        logger.warning(
            "seller quantity corrected from %s to %s for %s",
            check.proposed,
            check.accepted,
            ticker,
        )
    if check.accepted < 1:
        return None
    return tools.place_order(ticker, OrderSide.SELL, check.accepted)
