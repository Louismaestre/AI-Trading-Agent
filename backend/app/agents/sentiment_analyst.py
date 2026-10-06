"""Sentiment report from headlines already public at `as_of`. Edit the prompt, not this file."""

import datetime
from collections.abc import Sequence
from pathlib import Path

from app.llm import StructuredLLM
from app.schemas.agents import AnalystReport
from app.schemas.news import NewsItem
from app.services.news_text import format_brief

SYSTEM = (Path(__file__).resolve().parent / "prompts" / "sentiment_analyst.md").read_text(
    encoding="utf-8"
)

_NO_NEWS = AnalystReport(
    stance="NEUTRAL",
    confidence=0.2,
    rationale="No headlines at as_of.",
)


def report(
    llm: StructuredLLM,
    headlines: Sequence[NewsItem],
    as_of: datetime.date,
) -> AnalystReport:
    """Judge tone from `headlines`. Empty list → NEUTRAL, no LLM call."""
    if not headlines:
        return _NO_NEWS
    listed = "\n".join(format_brief(item) for item in headlines)
    user = f"""
    As of:
    {as_of}

    Headlines:
    {listed}
    """
    return llm.generate(AnalystReport, SYSTEM, user)
