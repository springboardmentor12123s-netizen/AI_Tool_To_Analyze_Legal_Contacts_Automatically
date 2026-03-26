from agents import compliance_agent, finance_agent, legal_agent
from planning_module import planning_agent
from aggregator import aggregate_results
from concurrent.futures import ThreadPoolExecutor


def coordinator(text):

    print("Step 1: Planning started")
    planning_result = planning_agent(text)

    execution_order = planning_result.get("execution_order", [])
    print("Execution Order:", execution_order)

    agent_results = {}

    print("Step 2: Running agents in parallel")

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

    print("Step 3: Aggregating results")

    final_results = aggregate_results(planning_result, agent_results)

    return final_results