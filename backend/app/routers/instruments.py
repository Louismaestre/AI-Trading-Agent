import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Instrument
from app.schemas.instrument import InstrumentResponse, SyncPricesRequest, SyncPricesResponse
from app.schemas.market import Bar
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService, UnknownTickerError

router = APIRouter(prefix="/instruments", tags=["instruments"])


def get_instrument_service(session: Annotated[Session, Depends(get_session)]) -> InstrumentService:
    return InstrumentService(session)


def get_market_data_service(
    session: Annotated[Session, Depends(get_session)],
) -> MarketDataService:
    return MarketDataService(session)


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown ticker: {ticker}"
        ) from None


@router.post("/sync-prices", response_model=SyncPricesResponse)
def sync_prices(
    request: SyncPricesRequest,
    service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> SyncPricesResponse:
    """Download the missing daily bars of every instrument from Yahoo Finance."""
    bars_stored = service.sync_universe_prices(request.start, request.end)
    return SyncPricesResponse(bars_stored=bars_stored)
