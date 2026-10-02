from dataclasses import dataclass
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import decide
from app.agents.buyer import execute as buy
from app.agents.debate import argue_bear, argue_bull
from app.agents.fundamental_analyst import report as fundamental_analyst
from app.agents.seller import execute as sell
from app.agents.sentiment_analyst import report as sentiment_analyst
from app.agents.state import AgentState
from app.agents.tools import AgentTools
from app.llm import StructuredLLM
from app.schemas.agents import AnalystReport, DebateArgument
from app.schemas.portfolio import PositionResponse

_MAX_DEBATE_ROUNDS = 3


@dataclass(frozen=True)
class GraphConfig:
    fundamental: bool = True
    sentiment: bool = True
    debate_rounds: int = 0


def build_graph(llm: StructuredLLM, tools: AgentTools, config: GraphConfig | None = None) -> object:
    """Specialists, optional bull/bear loop, then analyst, buyer, seller, or stop."""
    config = config or GraphConfig()
    rounds = max(0, min(_MAX_DEBATE_ROUNDS, config.debate_rounds))
    graph = StateGraph(AgentState)
    graph.add_node("analyst", lambda state: _analyst(state, llm, tools))
    graph.add_node("buyer", lambda state: _buyer(state, llm, tools))
    graph.add_node("seller", lambda state: _seller(state, llm, tools))
    graph.add_conditional_edges("analyst", _route)
    graph.add_edge("buyer", END)
    graph.add_edge("seller", END)
    specialists = [
        ("fundamental", config.fundamental, _fundamental),
        ("sentiment", config.sentiment, _sentiment),
    ]
    enabled = [(name, node) for name, on, node in specialists if on]
    after_specialists = "bull" if rounds else "analyst"
    if not enabled:
        graph.add_edge(START, after_specialists)
    for name, node in enabled:
        graph.add_node(name, lambda state, node=node: node(state, llm, tools))
        graph.add_edge(START, name)
        graph.add_edge(name, after_specialists)
    if rounds:
        graph.add_node("bull", lambda state: _researcher(state, llm, tools, "BULL"))
        graph.add_node("bear", lambda state: _researcher(state, llm, tools, "BEAR"))
        graph.add_edge("bull", "bear")
        graph.add_conditional_edges(
            "bear",
            lambda state, limit=rounds: _more_debate(state, limit),
            {"bull": "bull", "analyst": "analyst"},
        )

    return graph.compile()


def _analyst(state: AgentState, llm: StructuredLLM, tools: AgentTools) -> dict[str, object]:
    view = tools.get_position(state["ticker"])
    position = (
        PositionResponse(
            ticker=view.ticker,
            quantity=view.quantity,
            average_cost=view.average_cost,
            market_price=view.market_price,
            value=view.value,
        )
        if view is not None
        else None
    )
    return {
        "decision": decide(
            llm,
            state["summary"],
            position,
            state["as_of"],
            state.get("reports"),
            tools.get_prior_year_context(state["ticker"]),
            state.get("debate") or [],
        )
    }


def _fundamental(state: AgentState, llm: StructuredLLM, tools: AgentTools) -> dict[str, object]:
    snapshot = tools.get_fundamentals(state["ticker"])
    if snapshot is None:
        return {"reports": {}}
    try:
        report = fundamental_analyst(llm, snapshot)
    except Exception as exc:
        report = AnalystReport(stance="NEUTRAL", confidence=0, rationale=f"error: {exc}")
    return {"reports": {"fundamental": report}}


def _sentiment(state: AgentState, llm: StructuredLLM, tools: AgentTools) -> dict[str, object]:
    headlines = tools.get_news(state["ticker"])
    try:
        report = sentiment_analyst(llm, headlines, state["as_of"])
    except Exception as exc:
        report = AnalystReport(stance="NEUTRAL", confidence=0, rationale=f"error: {exc}")
    return {"reports": {"sentiment": report}}


def _researcher(
    state: AgentState,
    llm: StructuredLLM,
    tools: AgentTools,
    side: Literal["BULL", "BEAR"],
) -> dict[str, object]:
    argue = argue_bull if side == "BULL" else argue_bear
    try:
        argument = argue(
            llm,
            state["summary"],
            state.get("reports"),
            tools.get_prior_year_context(state["ticker"]),
            state.get("debate") or [],
            state["as_of"],
        )
    except Exception as exc:
        argument = DebateArgument(side=side, conviction=0, argument=f"error: {exc}")
    return {"debate": [argument]}


def _more_debate(state: AgentState, rounds: int) -> str:
    bears = sum(1 for item in state.get("debate") or [] if item.side == "BEAR")
    return "bull" if bears < rounds else "analyst"


def _buyer(state: AgentState, llm: StructuredLLM, tools: AgentTools) -> dict[str, object]:
    decision = state["decision"]
    if decision is None:
        return {"order": None}
    return {"order": buy(llm, tools, state["ticker"], decision)}


def _seller(state: AgentState, llm: StructuredLLM, tools: AgentTools) -> dict[str, object]:
    decision = state["decision"]
    if decision is None:
        return {"order": None}
    return {"order": sell(llm, tools, state["ticker"], decision)}


def _route(state: AgentState) -> str:
    decision = state["decision"]
    if decision is None or decision.action == "HOLD":
        return END
    if decision.action == "BUY":
        return "buyer"
    return "seller"
