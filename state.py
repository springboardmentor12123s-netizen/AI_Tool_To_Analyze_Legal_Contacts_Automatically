from typing import TypedDict, Dict, Any


class ContractState(TypedDict):
    contract_text: str
    planning_result: Dict[str, Any]
    agent_results: Dict[str, Any]
    final_report: Dict[str, Any]