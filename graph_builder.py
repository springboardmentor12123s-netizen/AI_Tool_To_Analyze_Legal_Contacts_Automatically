from langgraph.graph import StateGraph
from state import ContractState
from planning_module import planning_node
from analysis_nodes import execute_agents_node
from aggregator import aggregation_node


def build_graph():

    graph = StateGraph(ContractState)

    graph.add_node("planning", planning_node)
    graph.add_node("analysis", execute_agents_node)
    graph.add_node("reporting", aggregation_node)

    graph.set_entry_point("planning")

    graph.add_edge("planning", "analysis")
    graph.add_edge("analysis", "reporting")

    graph.set_finish_point("reporting")

    return graph.compile()