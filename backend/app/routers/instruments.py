import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Instrument
from app.schemas.fundamentals import FundamentalSnapshot
from app.schemas.instrument import (
    InstrumentResponse,
    SyncFundamentalsResponse,
    SyncIntradayRequest,
    SyncPricesRequest,
    SyncPricesResponse,
)
from app.schemas.market import Bar, IntradayBar
from app.services.fundamentals_service import FundamentalsService
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService, UnknownTickerError

router = APIRouter(prefix="/instruments", tags=["instruments"])


def get_instrument_service(session: Annotated[Session, Depends(get_session)]) -> InstrumentService:
    return InstrumentService(session)


def get_market_data_service(
    session: Annotated[Session, Depends(get_session)],
) -> MarketDataService:
    return MarketDataService(session)


def get_fundamentals_service(
    session: Annotated[Session, Depends(get_session)],
) -> FundamentalsService:
    return FundamentalsService(session)


@router.get("", response_model=list[InstrumentResponse])
def list_instruments(
    service: Annotated[InstrumentService, Depends(get_instrument_service)],
) -> list[Instrument]:
    return service.list_instruments()


@router.get("/{ticker}/prices", response_model=list[Bar])
def get_prices(
    ticker: str,
    start: datetime.date,
    end: datetime.date,
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> list[Bar]:
    """Stored daily bars between `start` and `end`, both included. 404 if the ticker is unknown."""
    try:
        return service.get_prices(ticker, start, end)
    except UnknownTickerError:
        raise _unknown_ticker(ticker) from None


@router.get("/{ticker}/intraday", response_model=list[IntradayBar])
def get_intraday(
    ticker: str,
    start: AwareDatetime,
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
    end: AwareDatetime | None = None,
) -> list[IntradayBar]:
    """Stored 5-minute bars from `start` to `end` (default: now). Times need a timezone."""
    try:
        return service.get_intraday(ticker, start, end or datetime.datetime.now(datetime.UTC))
    except UnknownTickerError:
        raise _unknown_ticker(ticker) from None


@router.get("/{ticker}/fundamentals", response_model=FundamentalSnapshot)
def get_fundamentals(
    ticker: str,
    service: Annotated[FundamentalsService, Depends(get_fundamentals_service)],
    as_of: datetime.date | None = None,
) -> FundamentalSnapshot:
    """Filings already public at `as_of` (default: today). 404 if the ticker is unknown."""
    try:
        return service.get_snapshot(ticker, as_of or datetime.date.today())
    except UnknownTickerError:
        raise _unknown_ticker(ticker) from None


@router.post("/sync-fundamentals", response_model=SyncFundamentalsResponse)
def sync_fundamentals(
    service: Annotated[FundamentalsService, Depends(get_fundamentals_service)],
) -> SyncFundamentalsResponse:
    """Download restated quarters for every tradable ticker from Yahoo Finance."""
    return SyncFundamentalsResponse(periods_stored=service.sync_universe())


@router.post("/sync-prices", response_model=SyncPricesResponse)
def sync_prices(
    request: SyncPricesRequest,
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> SyncPricesResponse:
    """Download the missing daily bars of every instrument from Yahoo Finance."""
    bars_stored = service.sync_universe_prices(request.start, request.end)
    return SyncPricesResponse(bars_stored=bars_stored)


@router.post("/sync-intraday", response_model=SyncPricesResponse)
def sync_intraday(
    request: SyncIntradayRequest,
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> SyncPricesResponse:
    """Download the 5-minute bars of every instrument from Yahoo Finance."""
    bars_stored = service.sync_universe_intraday(request.start)
    return SyncPricesResponse(bars_stored=bars_stored)


def _unknown_ticker(ticker: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown ticker: {ticker}")
