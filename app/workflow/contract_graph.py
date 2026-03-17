from langgraph.graph import StateGraph
from concurrent.futures import ThreadPoolExecutor

from app.agents.compliance_agent import ComplianceAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.legal_agent import LegalAgent
from app.agents.operations_agent import OperationsAgent

from app.services.clause_retriever import get_agent_context
from app.services.vector_store import store_agent_results


def agents_node(state):

    agents = {
        "legal": LegalAgent(),
        "finance": FinanceAgent(),
        "compliance": ComplianceAgent(),
        "operations": OperationsAgent()
    }

    results = {}

    def run_agent(agent_name):

        agent = agents[agent_name]

        context = get_agent_context(agent_name)

        result = agent.analyze(context)

        store_agent_results(agent_name, result)

        return agent_name, result

    with ThreadPoolExecutor() as executor:

        futures = [
            executor.submit(run_agent, name)
            for name in agents
        ]

        for future in futures:

            name, result = future.result()

            results[name] = result

    return {"results": results}


def build_graph():

    builder = StateGraph(dict)

    builder.add_node("agents", agents_node)

    builder.set_entry_point("agents")

    builder.set_finish_point("agents")

    return builder.compile()