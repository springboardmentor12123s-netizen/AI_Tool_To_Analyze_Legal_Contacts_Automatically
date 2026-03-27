from langgraph.graph import StateGraph, END
from typing import TypedDict

from agents import (
    compliance_agent,
    legal_agent,
    finance_agent,
    operations_agent,
    report_generator
)

class ContractState(TypedDict):
    contract: str
    compliance_result: str
    legal_result: str
    finance_result: str
    operations_result: str
    final_report: str
    tone: str
    focus: str

graph = StateGraph(ContractState)

graph.add_node("compliance", compliance_agent)
graph.add_node("legal", legal_agent)
graph.add_node("finance", finance_agent)
graph.add_node("operations", operations_agent)
graph.add_node("report", report_generator)

graph.set_entry_point("compliance")

graph.add_edge("compliance", "legal")
graph.add_edge("legal", "finance")
graph.add_edge("finance", "operations")
graph.add_edge("operations", "report")
graph.add_edge("report", END)

contract_graph = graph.compile()