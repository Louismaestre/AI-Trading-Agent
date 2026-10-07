"""YAML-backed experiment matrix. Every file shares the same trading window."""

import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.graph import GraphConfig
from app.services.portfolio_service import DEFAULT_CAPITAL


class ExperimentGraph(BaseModel):
    fundamental: bool = False
    sentiment: bool = False
    debate_rounds: int = Field(default=0, ge=0, le=3)
    risk: bool = False
    model: str | None = None

    def to_graph_config(self) -> GraphConfig:
        return GraphConfig(
            fundamental=self.fundamental,
            sentiment=self.sentiment,
            debate_rounds=self.debate_rounds,
            risk=self.risk,
        )


class ExperimentConfig(BaseModel):
    id: str = Field(min_length=1, max_length=16)
    name: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=400)
    start: datetime.date
    end: datetime.date
    initial_capital: Decimal = Field(default=DEFAULT_CAPITAL, gt=0)
    decision_frequency: Literal["DAILY", "WEEKLY"] = "WEEKLY"
    graph: ExperimentGraph = Field(default_factory=ExperimentGraph)


class ExperimentResponse(BaseModel):
    id: str
    name: str
    question: str
    start: datetime.date
    end: datetime.date
    initial_capital: Decimal
    decision_frequency: Literal["DAILY", "WEEKLY"]
    graph: ExperimentGraph
