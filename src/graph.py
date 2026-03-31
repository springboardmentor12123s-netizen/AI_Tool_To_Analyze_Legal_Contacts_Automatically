from langgraph.graph import StateGraph, END
from typing import TypedDict

from agents import compliance_agent, legal_agent, finance_agent, operations_agent


class ContractState(TypedDict):
    contract: str
    compliance_result: str
    legal_result: str
    finance_result: str
    operations_result: str


builder = StateGraph(ContractState)  # creates the langGraph workflow object

# Add nodes
builder.add_node("compliance", compliance_agent)
builder.add_node("legal", legal_agent)
builder.add_node("finance", finance_agent)
builder.add_node("operations", operations_agent)

# Entry point
builder.set_entry_point("compliance") # defines the execution order

# Edges
builder.add_edge("compliance", "legal")
builder.add_edge("legal", "finance")
builder.add_edge("finance", "operations")
builder.add_edge("operations", END)

# Compile graph
contract_graph = builder.compile() # creates the final execution pipeline