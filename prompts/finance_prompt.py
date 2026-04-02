from prompts.base_prompt import build_base_prompt

def finance_prompt(context: str):
    task = """
Identify payment risks, penalties, and financial exposure
based only on contract terms.
"""
    return build_base_prompt("Financial Analyst", task, context)