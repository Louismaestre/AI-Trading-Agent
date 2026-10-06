"""LLM risk opinion. It may only refuse or cut size; Python `enforce` still runs after."""

import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from app.agents.debate import format_transcript
from app.llm import StructuredLLM
from app.schemas.agents import AnalystDecision, AnalystReport, DebateArgument, RiskAssessment
from app.services.risk_rules import RiskBook

SYSTEM = (Path(__file__).resolve().parent / "prompts" / "risk_manager.md").read_text(
    encoding="utf-8"
)


def assess(
    llm: StructuredLLM,
    decision: AnalystDecision,
    book: RiskBook,
    reports: dict[str, AnalystReport] | None = None,
    debate: Sequence[DebateArgument] | None = None,
) -> RiskAssessment:
    """Ask the model to approve, cut, or refuse. Raw output — `enforce` caps it later."""
    reports_json = (
        json.dumps({name: report.model_dump(mode="json") for name, report in reports.items()})
        if reports
        else "none"
    )
    user = f"""
    Analyst decision:
    {decision.model_dump_json()}

    Risk book:
    {json.dumps(asdict(book), default=str)}

    Specialist reports:
    {reports_json}

    Debate transcript:
    {format_transcript(debate or [])}
    """
    return llm.generate(RiskAssessment, SYSTEM, user)
