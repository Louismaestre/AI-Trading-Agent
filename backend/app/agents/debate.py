"""Bull and bear researchers. They only argue; they never place an order."""

import datetime
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from app.llm import StructuredLLM
from app.schemas.agents import AnalystReport, DebateArgument, PriorYearContext, TechnicalSummary

_PROMPTS = Path(__file__).resolve().parent / "prompts"
BULL_SYSTEM = (_PROMPTS / "bull_researcher.md").read_text(encoding="utf-8")
BEAR_SYSTEM = (_PROMPTS / "bear_researcher.md").read_text(encoding="utf-8")


def format_transcript(arguments: Sequence[DebateArgument]) -> str:
    """Readable debate history for the next speaker. `none` if nobody has spoken."""
    if not arguments:
        return "none"
    return "\n".join(f"{item.side}: {item.argument}" for item in arguments)


def argue_bull(
    llm: StructuredLLM,
    summary: TechnicalSummary,
    reports: dict[str, AnalystReport] | None = None,
    prior_year: PriorYearContext | None = None,
    transcript: Sequence[DebateArgument] | None = None,
    as_of: datetime.date | None = None,
) -> DebateArgument:
    """One bullish turn. `side` is forced to BULL even if the model disagrees."""
    return _argue("BULL", BULL_SYSTEM, llm, summary, reports, prior_year, transcript, as_of)


def argue_bear(
    llm: StructuredLLM,
    summary: TechnicalSummary,
    reports: dict[str, AnalystReport] | None = None,
    prior_year: PriorYearContext | None = None,
    transcript: Sequence[DebateArgument] | None = None,
    as_of: datetime.date | None = None,
) -> DebateArgument:
    """One bearish turn. `side` is forced to BEAR even if the model disagrees."""
    return _argue("BEAR", BEAR_SYSTEM, llm, summary, reports, prior_year, transcript, as_of)


def _argue(
    side: Literal["BULL", "BEAR"],
    system: str,
    llm: StructuredLLM,
    summary: TechnicalSummary,
    reports: dict[str, AnalystReport] | None,
    prior_year: PriorYearContext | None,
    transcript: Sequence[DebateArgument] | None,
    as_of: datetime.date | None,
) -> DebateArgument:
    reports_json = (
        json.dumps({name: report.model_dump(mode="json") for name, report in reports.items()})
        if reports
        else "none"
    )
    user = f"""
    Technical summary:
    {summary.model_dump_json()}

    As of:
    {as_of if as_of is not None else "none"}

    Specialist reports:
    {reports_json}

    Prior completed year:
    {prior_year.model_dump_json() if prior_year is not None else "none"}

    Debate so far:
    {format_transcript(transcript or [])}
    """
    raw = llm.generate(DebateArgument, system, user)
    return raw.model_copy(update={"side": side})
