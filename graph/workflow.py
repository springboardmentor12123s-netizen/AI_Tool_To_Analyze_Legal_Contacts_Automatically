from typing import TypedDict, Optional
from langgraph.graph import StateGraph
from dotenv import load_dotenv
from modules.clients import get_clients
from modules.vector_store import retrieve_chunks

# LOAD ENV + GEMINI CLIENT
load_dotenv()
client, pc = get_clients()

# -----------------------------
# STATE
# -----------------------------
class ContractState(TypedDict):
    contract_text: str
    namespace: str
    contract_type: Optional[str]
    compliance: Optional[str]
    finance: Optional[str]
    legal: Optional[str]
    operations: Optional[str]
    risk_summary: Optional[str]
    final_report: Optional[str]

# -----------------------------
# NODE 1 — CLASSIFY (OPTIONAL)
# -----------------------------
def classify_contract(state: ContractState):

    prompt = f"""
    Classify this contract into ONE type:

    Employment, NDA, Vendor, Lease, Service Agreement, Other

    Answer in one word.

    Contract:
    {state["contract_text"][:1500]}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return {"contract_type": response.text.strip()}

# -----------------------------
# NODE 2 — PARALLEL RETRIEVAL (NO GEMINI)
# -----------------------------
def compliance_node(state: ContractState):

    chunks = retrieve_chunks(
        "compliance risks and regulatory issues",
        state["namespace"]
    )

    return {"compliance": "\n".join(chunks[:2])}


def finance_node(state: ContractState):

    chunks = retrieve_chunks(
        "financial terms payments penalties risks",
        state["namespace"]
    )

    return {"finance": "\n".join(chunks[:2])}


def legal_node(state: ContractState):

    chunks = retrieve_chunks(
        "legal clauses liabilities obligations risks",
        state["namespace"]
    )

    return {"legal": "\n".join(chunks[:2])}


def operations_node(state: ContractState):

    chunks = retrieve_chunks(
        "operational execution delivery timelines responsibilities",
        state["namespace"]
    )

    return {"operations": "\n".join(chunks[:2])}

# -----------------------------
# NODE 3 — MULTI-TURN REASONING (1 GEMINI CALL)
# -----------------------------
def summarize_risks(state: ContractState):

    prompt = f"""
    You are a senior contract analyst.

    Analyze the contract using the following domain inputs.

    Give output in bullet points only.

    COMPLIANCE:
    {state.get("compliance", "")}

    FINANCE:
    {state.get("finance", "")}

    LEGAL:
    {state.get("legal", "")}

    OPERATIONS:
    {state.get("operations", "")}

    OUTPUT FORMAT:

    COMPLIANCE:
    - point

    FINANCE:
    - point

    LEGAL:
    - point

    OPERATIONS:
    - point

    OVERALL RISKS:
    - point
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return {"risk_summary": response.text}

# -----------------------------
# NODE 4 — FINAL REPORT
# -----------------------------
def generate_final_report(state: ContractState):

    report = f"""
    CONTRACT TYPE:
    {state.get("contract_type", "")}

    ANALYSIS:
    {state.get("risk_summary", "")}
    """

    return {"final_report": report}

# -----------------------------
# GRAPH
# -----------------------------
builder = StateGraph(ContractState)

builder.add_node("classify", classify_contract)

builder.add_node("compliance", compliance_node)
builder.add_node("finance", finance_node)
builder.add_node("legal", legal_node)
builder.add_node("operations", operations_node)

builder.add_node("risk_summary", summarize_risks)
builder.add_node("final", generate_final_report)

# ENTRY
builder.set_entry_point("classify")

# PARALLEL EXECUTION
builder.add_edge("classify", "compliance")
builder.add_edge("classify", "finance")
builder.add_edge("classify", "legal")
builder.add_edge("classify", "operations")

# SYNC ALL → ONE REASONING STEP
builder.add_edge(
    ["compliance", "finance", "legal", "operations"],
    "risk_summary"
)

# FINAL
builder.add_edge("risk_summary", "final")

# COMPILE
graph = builder.compile()