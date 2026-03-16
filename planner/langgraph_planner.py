from langgraph.graph import StateGraph, START, END
from typing import TypedDict

from agents.legal_agent import analyze_legal
from agents.finance_agent import analyze_finance
from agents.compliance_agent import analyze_compliance
from agents.operations_agent import analyze_operations


from rag.store_intermediate import store_agent_result


class ContractState(TypedDict):
    text: str

    legal_r1: str
    finance_r1: str
    compliance_r1: str
    operations_r1: str

    legal_r2: str
    finance_r2: str
    compliance_r2: str
    operations_r2: str


# -------------------------
# ROUND 1 (parallel agents)
# -------------------------

def legal_r1_node(state):
    result = analyze_legal(state["text"])
    analysis=result["analysis"]
    store_agent_result("legal_r1", "contract1", analysis)
    return {"legal_r1": analysis}


def finance_r1_node(state):
    result = analyze_finance(state["text"])
    analysis=result["analysis"]
    store_agent_result("finance_r1", "contract1", analysis)
    return {"finance_r1": analysis}


def compliance_r1_node(state):
    result = analyze_compliance(state["text"])
    analysis=result["analysis"]
    store_agent_result("compliance_r1", "contract1", analysis)
    return {"compliance_r1": analysis}


def operations_r1_node(state):
    result = analyze_operations(state["text"])
    analysis=result["analysis"]
    store_agent_result("operations_r1", "contract1", analysis)
    return {"operations_r1": analysis}


# -------------------------
# Build Multi-Agent Context
# -------------------------

def build_context(state):

    return f"""
Contract:
{state['text']}

Legal Findings:
{state['legal_r1']}

Finance Findings:
{state['finance_r1']}

Compliance Findings:
{state['compliance_r1']}

Operations Findings:
{state['operations_r1']}
"""


# -------------------------
# ROUND 2 (multi-turn agents)
# -------------------------

def legal_r2_node(state):

    context = build_context(state)
    result = analyze_legal(context)
    analysis=result["analysis"]
    store_agent_result("legal_r2", "contract1", analysis)

    return {"legal_r2": analysis}


def finance_r2_node(state):

    context = build_context(state)
    result = analyze_finance(context)
    analysis=result["analysis"]
    store_agent_result("finance_r2", "contract1", analysis)

    return {"finance_r2": analysis}


def compliance_r2_node(state):

    context = build_context(state)
    result = analyze_compliance(context)
    analysis=result["analysis"]
    store_agent_result("compliance_r2", "contract1", analysis)

    return {"compliance_r2": analysis}


def operations_r2_node(state):

    context = build_context(state)
    result = analyze_operations(context)
    analysis = result["analysis"]
    store_agent_result("operations_r2", "contract1", analysis)

    return {"operations_r2": analysis}


# -------------------------
# Synchronization Node
# -------------------------

def sync_node(state):
    """
    Barrier node that waits until all
    Round-1 agents complete.
    """
    return state


# -------------------------
# LangGraph Pipeline
# -------------------------

def run_langgraph(contract_text):

    graph = StateGraph(ContractState)

    # Round 1 agents
    graph.add_node("legal_r1", legal_r1_node)
    graph.add_node("finance_r1", finance_r1_node)
    graph.add_node("compliance_r1", compliance_r1_node)
    graph.add_node("operations_r1", operations_r1_node)

    # Sync node
    graph.add_node("sync", sync_node)

    # Round 2 agents
    graph.add_node("legal_r2", legal_r2_node)
    graph.add_node("finance_r2", finance_r2_node)
    graph.add_node("compliance_r2", compliance_r2_node)
    graph.add_node("operations_r2", operations_r2_node)

    # -------------------------
    # ROUND 1 PARALLEL
    # -------------------------

    graph.add_edge(START, "legal_r1")
    graph.add_edge(START, "finance_r1")
    graph.add_edge(START, "compliance_r1")
    graph.add_edge(START, "operations_r1")

    # -------------------------
    # WAIT FOR ALL AGENTS
    # -------------------------

    graph.add_edge("legal_r1", "sync")
    graph.add_edge("finance_r1", "sync")
    graph.add_edge("compliance_r1", "sync")
    graph.add_edge("operations_r1", "sync")

    # -------------------------
    # ROUND 2 PARALLEL
    # -------------------------

    graph.add_edge("sync", "legal_r2")
    graph.add_edge("sync", "finance_r2")
    graph.add_edge("sync", "compliance_r2")
    graph.add_edge("sync", "operations_r2")

    # -------------------------
    # END
    # -------------------------

    graph.add_edge("legal_r2", END)
    graph.add_edge("finance_r2", END)
    graph.add_edge("compliance_r2", END)
    graph.add_edge("operations_r2", END)

    app = graph.compile()

    return app.invoke({
        "text": contract_text,

        "legal_r1": "",
        "finance_r1": "",
        "compliance_r1": "",
        "operations_r1": "",

        "legal_r2": "",
        "finance_r2": "",
        "compliance_r2": "",
        "operations_r2": ""
    })