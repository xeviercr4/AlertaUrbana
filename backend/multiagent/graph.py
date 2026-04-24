from langgraph.graph import StateGraph, END
from .state import AgentState

from .agents.planner import planner_node
from .agents.researcher import researcher_node
from .agents.analyst import analyst_node
from .agents.decision import decision_node
from .agents.writer import writer_node
from .agents.verifier import verifier_node


def build_graph():

    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("decision", decision_node)
    builder.add_node("writer", writer_node)
    builder.add_node("verifier", verifier_node)

    builder.set_entry_point("planner")

    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst", "decision")
    builder.add_edge("decision", "writer")
    builder.add_edge("writer", "verifier")
    builder.add_edge("verifier", END)

    return builder.compile()