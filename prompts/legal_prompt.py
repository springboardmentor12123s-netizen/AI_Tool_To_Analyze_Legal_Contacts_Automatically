from prompts.base_prompt import build_base_prompt

def legal_prompt(context: str):
    task = """
Identify key legal clauses, termination conditions,
and liability exposure strictly from the contract.
"""
    return build_base_prompt("Legal Contract Analyst", task, context)