from langgraph.graph import END, START, StateGraph

from app.agents.analyst import decide
from app.agents.buyer import execute as buy
from app.agents.seller import execute as sell
from app.agents.state import AgentState
from app.agents.tools import AgentTools
from app.llm import StructuredLLM
from app.schemas.portfolio import PositionResponse


def build_graph(llm: StructuredLLM, tools: AgentTools) -> object:
    """Analyst then buyer, seller, or stop, depending on the decision."""
    graph = StateGraph(AgentState)
    graph.add_node("analyst", lambda state: _analyst(state, llm, tools))
    graph.add_node("buyer", lambda state: _buyer(state, llm, tools))
    graph.add_node("seller", lambda state: _seller(state, llm, tools))
    graph.add_edge(START, "analyst")
    graph.add_conditional_edges("analyst", _route)
    graph.add_edge("buyer", END)
    graph.add_edge("seller", END)
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
    return {"decision": decide(llm, state["summary"], position, state["as_of"])}


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
