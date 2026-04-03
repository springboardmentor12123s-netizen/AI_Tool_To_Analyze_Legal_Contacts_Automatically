import concurrent.futures
from typing import TypedDict

from agents import compliance_agent, finance_agent, legal_agent, operations_agent


class ContractState(TypedDict, total=False):
    contract: str
    compliance_result: str
    legal_result: str
    finance_result: str
    operations_result: str


def run_all_agents(state: ContractState) -> ContractState:
    agents = [compliance_agent, legal_agent, finance_agent, operations_agent]
    results: ContractState = dict(state)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(agent, dict(state)): agent for agent in agents}
        for future in concurrent.futures.as_completed(future_map):
            payload = future.result() or {}
            if isinstance(payload, dict):
                results.update(payload)
    return results


class _CompiledGraph:
    def invoke(self, state: ContractState) -> ContractState:
        return run_all_agents(state)


contract_graph = _CompiledGraph()
