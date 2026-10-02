from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from app.agents.analyst import decide
from app.agents.buyer import execute as buy
from app.agents.fundamental_analyst import report as fundamental_analyst
from app.agents.seller import execute as sell
from app.agents.sentiment_analyst import report as sentiment_analyst
from app.agents.state import AgentState
from app.agents.tools import AgentTools
from app.llm import StructuredLLM
from app.schemas.agents import AnalystReport
from app.schemas.portfolio import PositionResponse


@dataclass(frozen=True)
class GraphConfig:
    fundamental: bool = True
    sentiment: bool = True


def build_graph(llm: StructuredLLM, tools: AgentTools, config: GraphConfig | None = None) -> object:
    """Analyst then buyer, seller, or stop, depending on the decision."""
    config = config or GraphConfig()
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
    if not enabled:
        graph.add_edge(START, "analyst")
    for name, node in enabled:
        graph.add_node(name, lambda state, node=node: node(state, llm, tools))
        graph.add_edge(START, name)
        graph.add_edge(name, "analyst")

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
