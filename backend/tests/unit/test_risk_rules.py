from decimal import Decimal

from app.schemas.agents import AnalystDecision, RiskAssessment
from app.services.risk_rules import (
    RULE_ATR_SIZE,
    RULE_LLM_REFUSED,
    RULE_MAX_ORDERS,
    RULE_MAX_SECTOR,
    RULE_MAX_WEIGHT,
    RULE_MIN_CASH,
    RULE_MIN_CONFIDENCE,
    PositionRisk,
    RiskBook,
    apply_rules,
    enforce,
    stop_loss_hit,
)


def _buy(weight: float = 0.20, confidence: float = 0.8) -> AnalystDecision:
    return AnalystDecision(
        action="BUY", confidence=confidence, target_weight=weight, rationale="setup"
    )


def _book(
    *,
    ticker: str = "MC.PA",
    sector: str = "Luxury",
    total: str = "100000",
    cash: str = "100000",
    positions: tuple[PositionRisk, ...] = (),
    orders_today: int = 0,
    atr: Decimal | None = None,
    last_price: Decimal | None = None,
) -> RiskBook:
    return RiskBook(
        ticker=ticker,
        sector=sector,
        total_value=Decimal(total),
        cash=Decimal(cash),
        positions=positions,
        orders_today=orders_today,
        atr=atr,
        last_price=last_price,
    )


def test_max_weight_caps_a_buy() -> None:
    result = apply_rules(_buy(0.40), _book())
    assert result.approved is True
    assert result.target_weight == 0.15
    assert RULE_MAX_WEIGHT in result.triggered_rules


def test_sector_cap_cannot_be_exceeded() -> None:
    held = PositionRisk(
        ticker="KER.PA",
        sector="Luxury",
        value=Decimal("25000"),
        quantity=10,
        average_cost=Decimal("250"),
        market_price=Decimal("250"),
    )
    result = apply_rules(_buy(0.15), _book(positions=(held,)))
    assert result.target_weight == 0.05
    assert RULE_MAX_SECTOR in result.triggered_rules


def test_min_cash_keeps_the_reserve() -> None:
    result = apply_rules(_buy(0.15), _book(cash="12000"))
    assert result.target_weight == 0.02
    assert RULE_MIN_CASH in result.triggered_rules


def test_too_many_orders_block_a_trade() -> None:
    result = apply_rules(_buy(), _book(orders_today=8))
    assert result.approved is False
    assert result.action == "HOLD"
    assert RULE_MAX_ORDERS in result.triggered_rules


def test_low_confidence_blocks_a_trade() -> None:
    result = apply_rules(_buy(confidence=0.2), _book())
    assert result.approved is False
    assert RULE_MIN_CONFIDENCE in result.triggered_rules


def test_atr_reduces_size() -> None:
    result = apply_rules(
        _buy(0.15),
        _book(atr=Decimal("20"), last_price=Decimal("500")),
    )
    assert result.target_weight == 0.15 * (0.02 / 0.04)
    assert RULE_ATR_SIZE in result.triggered_rules


def test_stop_loss_detects_a_ten_percent_drop() -> None:
    assert stop_loss_hit(Decimal("100"), Decimal("90"), 0.10) is True
    assert stop_loss_hit(Decimal("100"), Decimal("91"), 0.10) is False


def test_sell_is_not_blocked_by_max_weight() -> None:
    sell = AnalystDecision(action="SELL", confidence=0.8, target_weight=0, rationale="exit")
    result = apply_rules(sell, _book())
    assert result.approved is True
    assert result.action == "SELL"


def test_llm_cannot_raise_the_weight() -> None:
    llm = RiskAssessment(approved=True, action="BUY", target_weight=0.50)
    final, _assessment = enforce(_buy(0.10), _book(), llm)
    assert final.target_weight == 0.10


def test_llm_refuse_means_hold_and_no_size() -> None:
    llm = RiskAssessment(approved=False, action="HOLD", target_weight=0.10, reasons=["crowded"])
    final, assessment = enforce(_buy(0.10), _book(), llm)
    assert final.action == "HOLD"
    assert final.target_weight == 0
    assert assessment.approved is False
    assert RULE_LLM_REFUSED in assessment.triggered_rules
