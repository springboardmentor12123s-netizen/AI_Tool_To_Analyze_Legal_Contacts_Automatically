from prompts.base_prompt import build_base_prompt

def operations_prompt(context: str):
    task = """
Identify execution risks, delivery challenges,
and operational dependencies from the contract.
"""
    return build_base_prompt("Operations Analyst", task, context)