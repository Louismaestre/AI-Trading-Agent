import datetime

from fastapi import APIRouter
from pydantic import AwareDatetime

from app import market_clock
from app.schemas.market import MarketStatus

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/status", response_model=MarketStatus)
def get_market_status(at: AwareDatetime | None = None) -> MarketStatus:
    """Whether Euronext Paris is open at `at` (default: now), with the next open and last close."""
    now = at or datetime.datetime.now(datetime.UTC)
    return MarketStatus(
        now=now,
        is_open=market_clock.is_market_open(now),
        next_open=market_clock.next_open(now),
        last_close=market_clock.last_close(now),
    )
