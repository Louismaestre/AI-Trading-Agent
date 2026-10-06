"""API shapes for instruments and price synchronization."""

import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


def _three_years_ago() -> datetime.date:
    return datetime.date.today() - datetime.timedelta(days=3 * 365)


def _five_days_ago() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=5)


class InstrumentResponse(BaseModel):
    """Public view of an instrument; hides database ids and timestamps."""

    model_config = ConfigDict(from_attributes=True)

    ticker: str
    name: str
    isin: str | None
    sector: str | None
    currency: str
    is_active: bool


class SyncPricesRequest(BaseModel):
    """Period to download. Defaults to the last 3 years."""

    # default_factory runs on each request; a plain default would be frozen at startup.
    start: datetime.date = Field(default_factory=_three_years_ago)
    end: datetime.date = Field(default_factory=datetime.date.today)


class SyncIntradayRequest(BaseModel):
    """Start of the 5-minute bars to download (Yahoo keeps 60 days). Defaults to 5 days ago."""

    # AwareDatetime rejects "10:00" without a timezone with a 422.
    start: AwareDatetime = Field(default_factory=_five_days_ago)


class SyncPricesResponse(BaseModel):
    bars_stored: int


class SyncFundamentalsResponse(BaseModel):
    periods_stored: int
