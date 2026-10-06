"""Reference strategies. They produce the same AnalystDecision shape as the graph."""

import datetime
import random
from decimal import Decimal

from app.schemas.agents import Action, AnalystDecision, TechnicalSummary

_HOLD = AnalystDecision(action="HOLD", confidence=1, target_weight=0, rationale="no signal")


def sma_crossover_decision(
    summary: TechnicalSummary,
    held: bool,
    target_weight: float,
) -> AnalystDecision:
    """Buy when SMA 20 is above SMA 50, sell when it crosses back below."""
    if summary.sma_20 is None or summary.sma_50 is None:
        return _HOLD
    if summary.sma_20 > summary.sma_50:
        return AnalystDecision(
            action="BUY",
            confidence=1,
            target_weight=target_weight,
            rationale="SMA 20 above SMA 50",
        )
    if held:
        return AnalystDecision(
            action="SELL",
            confidence=1,
            target_weight=0,
            rationale="SMA 20 below SMA 50",
        )
    return _HOLD


def random_decision(
    ticker: str,
    as_of: datetime.date,
    seed: int,
    held: bool,
    target_weight: float,
) -> AnalystDecision:
    """Fixed-seed pick. The same (seed, ticker, day) always yields the same action."""
    rng = random.Random(f"{seed}|{ticker}|{as_of.isoformat()}")
    pick: Action = rng.choice(("BUY", "SELL", "HOLD"))
    if pick == "SELL" and not held:
        pick = "HOLD"
    if pick == "HOLD":
        return _HOLD
    if pick == "BUY":
        return AnalystDecision(
            action="BUY",
            confidence=1,
            target_weight=target_weight,
            rationale="random buy",
        )
    return AnalystDecision(action="SELL", confidence=1, target_weight=0, rationale="random sell")


def equal_weight(count: int) -> float:
    if count < 1:
        return 0
    return float(Decimal(1) / Decimal(count))
