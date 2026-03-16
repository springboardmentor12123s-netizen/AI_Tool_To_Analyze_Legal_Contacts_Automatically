from prompts.base_prompt import build_base_prompt

def legal_prompt(context: str):
    task = """
Analyze legal risks, important clauses, termination provisions,
and liability exposure in the contract.
"""
    return build_base_prompt("Legal Contract Analyst", task, context)