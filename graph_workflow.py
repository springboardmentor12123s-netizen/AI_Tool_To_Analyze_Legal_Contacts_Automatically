from langgraph.graph import StateGraph, END
from typing import TypedDict


# ---------------------------------------
# Shared State
# ---------------------------------------
class ContractState(TypedDict):
    compliance_text: str
    legal_text: str
    finance_text: str
    operations_text: str

    compliance_report: str
    legal_report: str
    finance_report: str
    operations_report: str


# ---------------------------------------
# Create Workflow (Hybrid Parallel + Multi-turn)
# ---------------------------------------
def create_workflow(
    run_agent,
    compliance_prompt,
    legal_prompt,
    finance_prompt,
    operations_prompt
):

    # ---------------------------------------
    # Parallel Agents
    # ---------------------------------------
    def compliance_node(state: ContractState):
        result = run_agent(
            compliance_prompt,
            state.get("compliance_text", "")
        )

        return {"compliance_report": result}


    def legal_node(state: ContractState):
        result = run_agent(
            legal_prompt,
            state.get("legal_text", "")
        )

        return {"legal_report": result}


    def finance_node(state: ContractState):
        result = run_agent(
            finance_prompt,
            state.get("finance_text", "")
        )

        return {"finance_report": result}


    # ---------------------------------------
    # Aggregator (Multi-turn reasoning)
    # ---------------------------------------
    def operations_node(state: ContractState):

        combined_input = f"""
Contract:
{state.get("operations_text", "")}

Compliance Findings:
{state.get("compliance_report", "")}

Legal Findings:
{state.get("legal_report", "")}

Financial Findings:
{state.get("finance_report", "")}

Task:
- Identify operational risks
- Combine cross-domain insights
- Provide final recommendations
"""

        result = run_agent(operations_prompt, combined_input)

        return {"operations_report": result}


    # ---------------------------------------
    # Build Graph
    # ---------------------------------------
    workflow = StateGraph(ContractState)

    # Add nodes
    workflow.add_node("compliance", compliance_node)
    workflow.add_node("legal", legal_node)
    workflow.add_node("finance", finance_node)
    workflow.add_node("operations", operations_node)

    # ---------------------------------------
    # ENTRY POINT (Correct way ✅)
    # ---------------------------------------
    workflow.set_entry_point("compliance")

    # ---------------------------------------
    # PARALLEL BRANCHING (fan-out)
    # ---------------------------------------
    workflow.add_edge("compliance", "legal")
    workflow.add_edge("compliance", "finance")

    # ---------------------------------------
    # MERGE INTO OPERATIONS (fan-in)
    # ---------------------------------------
    workflow.add_edge("legal", "operations")
    workflow.add_edge("finance", "operations")

    # Finish
    workflow.add_edge("operations", END)

    return workflow.compile()