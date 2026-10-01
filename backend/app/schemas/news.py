"""News headlines stored for the sentiment analyst."""

import datetime

from pydantic import BaseModel, ConfigDict, Field


class NewsItem(BaseModel):
    """One article as stored. `published_at` is timezone-aware."""

    model_config = ConfigDict(from_attributes=True)

    published_at: datetime.datetime
    source: str
    title: str
    summary: str | None = None
    url: str


class SyncNewsResponse(BaseModel):
    articles_stored: int


class NewsBrief(BaseModel):
    """Compact line for an agent prompt."""

    published_at: datetime.datetime
    source: str
    title: str
    summary: str | None = None
    brief: str = Field(description="date · source · title — truncated summary")
