from langgraph.graph import StateGraph, START, END
from typing import TypedDict

from agents.legal_agent import analyze_legal
from agents.finance_agent import analyze_finance
from agents.compliance_agent import analyze_compliance
from agents.operations_agent import analyze_operations

from rag.store_intermediate import store_agent_result


# -------------------------
# STATE
# -------------------------

class ContractState(TypedDict):
    text: str
    contract_id: str

    legal_r1: str
    finance_r1: str
    compliance_r1: str
    operations_r1: str

    legal_r2: str
    finance_r2: str
    compliance_r2: str
    operations_r2: str


# -------------------------
# ROUND 1 (PARALLEL)
# -------------------------

def legal_r1_node(state):
    result = analyze_legal(state["contract_id"])
    analysis = result["analysis"]

    store_agent_result("legal_r1", state["contract_id"], analysis)

    return {"legal_r1": analysis}


def finance_r1_node(state):
    result = analyze_finance(state["contract_id"])
    analysis = result["analysis"]

    store_agent_result("finance_r1", state["contract_id"], analysis)

    return {"finance_r1": analysis}


def compliance_r1_node(state):
    result = analyze_compliance(state["contract_id"])
    analysis = result["analysis"]

    store_agent_result("compliance_r1", state["contract_id"], analysis)

    return {"compliance_r1": analysis}


def operations_r1_node(state):
    result = analyze_operations(state["contract_id"])
    analysis = result["analysis"]

    store_agent_result("operations_r1", state["contract_id"], analysis)

    return {"operations_r1": analysis}


# -------------------------
# BUILD CONTEXT
# -------------------------

def build_context(state):
    return f"""
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
# ROUND 2 (MULTI-TURN)
# -------------------------

def legal_r2_node(state):
    context = build_context(state)


    result = analyze_legal(
    state["contract_id"],
    extra_context=context
)
    analysis = result["analysis"]

    store_agent_result("legal_r2", state["contract_id"], analysis)

    return {"legal_r2": analysis}


def finance_r2_node(state):

    context = build_context(state)

    result = analyze_finance(
    state["contract_id"],
    extra_context=context
)
    analysis = result["analysis"]

    store_agent_result("finance_r2", state["contract_id"], analysis)

    return {"finance_r2": analysis}


def compliance_r2_node(state):
    context = build_context(state)

    result = analyze_compliance(
    state["contract_id"],
    extra_context=context
)
    analysis = result["analysis"]

    store_agent_result("compliance_r2", state["contract_id"], analysis)

    return {"compliance_r2": analysis}


def operations_r2_node(state):
    context = build_context(state)

    result = analyze_operations(
    state["contract_id"],
    extra_context=context
)
    analysis = result["analysis"]

    store_agent_result("operations_r2", state["contract_id"], analysis)

    return {"operations_r2": analysis}


# -------------------------
# SYNC NODE
# -------------------------

def sync_node(state):
    return state


# -------------------------
# MAIN GRAPH
# -------------------------

def run_langgraph(contract_text, contract_id):

    graph = StateGraph(ContractState)

    # Round 1
    graph.add_node("legal_r1", legal_r1_node)
    graph.add_node("finance_r1", finance_r1_node)
    graph.add_node("compliance_r1", compliance_r1_node)
    graph.add_node("operations_r1", operations_r1_node)

    # Sync
    graph.add_node("sync", sync_node)

    # Round 2
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
    # SYNC
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
        "contract_id": contract_id,

        "legal_r1": "",
        "finance_r1": "",
        "compliance_r1": "",
        "operations_r1": "",

        "legal_r2": "",
        "finance_r2": "",
        "compliance_r2": "",
        "operations_r2": ""
    })