from concurrent.futures import ThreadPoolExecutor
from agents import legal_agent, finance_agent, compliance_agent
from clause_extractor import extract_clauses


def execute_agents_node(state: dict):

    text = state["contract_text"]
    planning = state["planning_result"]

    # ✅ Step 1: Extract clauses (Milestone 3)
    clauses = extract_clauses(text)
    text = "\n".join(clauses[:5])  # limit for speed

    execution_order = planning.get("execution_order", [])

    agent_results = {}

    # ✅ Step 2: Run agents in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:

        futures = {}

        if "legal" in execution_order:
            futures["legal"] = executor.submit(legal_agent, text)

        if "finance" in execution_order:
            futures["finance"] = executor.submit(finance_agent, text)

        if "compliance" in execution_order:
            futures["compliance"] = executor.submit(compliance_agent, text)

        for key, future in futures.items():
            agent_results[key] = future.result()

    return {
        "agent_results": agent_results
    }