"""Hard risk limits. Pure functions: the LLM cannot raise a weight or bypass a refuse."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.schemas.agents import Action, AnalystDecision, RiskAssessment

RULE_MAX_WEIGHT = "max_weight"
RULE_MAX_SECTOR = "max_sector_weight"
RULE_MIN_CASH = "min_cash"
RULE_MAX_ORDERS = "max_orders_per_day"
RULE_MIN_CONFIDENCE = "min_confidence"
RULE_ATR_SIZE = "atr_sizing"
RULE_STOP_LOSS = "stop_loss"
RULE_LLM_REFUSED = "llm_refused"


@dataclass(frozen=True)
class RiskLimits:
    max_weight: float = 0.15
    max_sector_weight: float = 0.30
    min_cash_weight: float = 0.10
    max_orders_per_day: int = 8
    min_confidence: float = 0.40
    stop_loss: float = 0.10
    atr_reference: float = 0.02


@dataclass(frozen=True)
class PositionRisk:
    ticker: str
    sector: str
    value: Decimal
    quantity: int
    average_cost: Decimal
    market_price: Decimal


@dataclass(frozen=True)
class RiskBook:
    ticker: str
    sector: str
    total_value: Decimal
    cash: Decimal
    positions: tuple[PositionRisk, ...]
    orders_today: int
    atr: Decimal | None = None
    last_price: Decimal | None = None


def stop_loss_hit(average_cost: Decimal, close: Decimal, stop_loss: float) -> bool:
    """True when `close` is at least `stop_loss` below the average cost."""
    if average_cost <= 0:
        return False
    return close <= average_cost * (Decimal("1") - Decimal(str(stop_loss)))


def merge_llm_assessment(decision: AnalystDecision, llm: RiskAssessment) -> AnalystDecision:
    """The LLM may only refuse or cut size. It cannot raise a weight or flip BUY to SELL."""
    if not llm.approved:
        return decision.model_copy(update={"action": "HOLD", "target_weight": 0.0})
    weight = min(decision.target_weight, llm.target_weight)
    action: Action = decision.action
    if action == "BUY" and weight <= 0:
        action = "HOLD"
    return decision.model_copy(update={"action": action, "target_weight": weight})


def enforce(
    decision: AnalystDecision,
    book: RiskBook,
    llm: RiskAssessment | None = None,
    limits: RiskLimits | None = None,
) -> tuple[AnalystDecision, RiskAssessment]:
    """Optional LLM verdict, then Python rules. Call this after the risk-manager agent."""
    proposed = merge_llm_assessment(decision, llm) if llm is not None else decision
    assessment = apply_rules(proposed, book, limits or RiskLimits())
    if llm is not None and not llm.approved:
        assessment = assessment.model_copy(
            update={
                "approved": False,
                "triggered_rules": [RULE_LLM_REFUSED, *assessment.triggered_rules],
            }
        )
    final = proposed.model_copy(
        update={"action": assessment.action, "target_weight": assessment.target_weight}
    )
    return final, assessment


def apply_rules(
    decision: AnalystDecision,
    book: RiskBook,
    limits: RiskLimits | None = None,
) -> RiskAssessment:
    """Cap or refuse. Never increases `target_weight` or turns HOLD into a trade."""
    limits = limits or RiskLimits()
    if decision.action == "HOLD":
        return RiskAssessment(approved=True, action="HOLD", target_weight=0.0)

    if decision.confidence < limits.min_confidence:
        return _refuse(RULE_MIN_CONFIDENCE, "confidence below the minimum")
    if book.orders_today >= limits.max_orders_per_day:
        return _refuse(RULE_MAX_ORDERS, "daily order budget already used")
    if decision.action == "SELL":
        return RiskAssessment(approved=True, action="SELL", target_weight=decision.target_weight)

    weight = decision.target_weight
    triggered: list[str] = []
    reasons: list[str] = []
    weight, hit, reason = _cap_max_weight(weight, limits)
    _record(triggered, reasons, hit, reason)
    weight, hit, reason = _cap_sector(weight, book, limits)
    _record(triggered, reasons, hit, reason)
    weight, hit, reason = _cap_cash(weight, book, limits)
    _record(triggered, reasons, hit, reason)
    weight, hit, reason = _cap_atr(weight, book, limits)
    _record(triggered, reasons, hit, reason)
    if weight <= 0:
        return _refuse(triggered[-1] if triggered else RULE_MAX_WEIGHT, "size cut to zero")
    return RiskAssessment(
        approved=True,
        action="BUY",
        target_weight=weight,
        reasons=reasons,
        triggered_rules=triggered,
    )


def _cap_max_weight(weight: float, limits: RiskLimits) -> tuple[float, str | None, str]:
    if weight <= limits.max_weight:
        return weight, None, ""
    return limits.max_weight, RULE_MAX_WEIGHT, f"weight capped at {limits.max_weight}"


def _cap_sector(weight: float, book: RiskBook, limits: RiskLimits) -> tuple[float, str | None, str]:
    if book.total_value <= 0:
        return weight, None, ""
    others = sum(
        (
            item.value
            for item in book.positions
            if item.sector == book.sector and item.ticker != book.ticker
        ),
        start=Decimal("0"),
    )
    allowed = Decimal(str(limits.max_sector_weight)) * book.total_value - others
    cap = float(max(Decimal("0"), allowed) / book.total_value)
    if weight <= cap:
        return weight, None, ""
    return cap, RULE_MAX_SECTOR, f"sector {book.sector} capped at {limits.max_sector_weight}"


def _cap_cash(weight: float, book: RiskBook, limits: RiskLimits) -> tuple[float, str | None, str]:
    if book.total_value <= 0:
        return weight, None, ""
    current = _current_weight(book)
    spend = (Decimal(str(weight)) - current) * book.total_value
    if spend <= 0:
        return weight, None, ""
    floor = Decimal(str(limits.min_cash_weight)) * book.total_value
    max_spend = book.cash - floor
    if max_spend <= 0:
        return float(current) if current > 0 else 0.0, RULE_MIN_CASH, "cash reserve would break"
    cap = float(current + max_spend / book.total_value)
    if weight <= cap:
        return weight, None, ""
    return max(0.0, cap), RULE_MIN_CASH, f"cash reserve {limits.min_cash_weight} kept"


def _cap_atr(weight: float, book: RiskBook, limits: RiskLimits) -> tuple[float, str | None, str]:
    if book.atr is None or book.last_price is None or book.last_price <= 0:
        return weight, None, ""
    vol = float(book.atr / book.last_price)
    if vol <= 0:
        return weight, None, ""
    scaled = weight * (limits.atr_reference / vol)
    if scaled >= weight:
        return weight, None, ""
    return scaled, RULE_ATR_SIZE, "size cut because ATR is high"


def _current_weight(book: RiskBook) -> Decimal:
    held = next((item for item in book.positions if item.ticker == book.ticker), None)
    if held is None or book.total_value <= 0:
        return Decimal("0")
    return held.value / book.total_value


def _record(triggered: list[str], reasons: list[str], rule: str | None, reason: str) -> None:
    if rule is None:
        return
    triggered.append(rule)
    reasons.append(reason)


def _refuse(rule: str, reason: str) -> RiskAssessment:
    return RiskAssessment(
        approved=False,
        action="HOLD",
        target_weight=0.0,
        reasons=[reason],
        triggered_rules=[rule],
    )


def stop_loss_tickers(
    positions: Sequence[PositionRisk],
    stop_loss: float,
) -> list[str]:
    """Names whose `market_price` (previous close) breached the stop."""
    return [
        item.ticker
        for item in positions
        if stop_loss_hit(item.average_cost, item.market_price, stop_loss)
    ]
