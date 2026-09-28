"""API shapes for instruments and price synchronization."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


def _three_years_ago() -> datetime.date:
    return datetime.date.today() - datetime.timedelta(days=3 * 365)


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


class SyncPricesResponse(BaseModel):
    bars_stored: int
