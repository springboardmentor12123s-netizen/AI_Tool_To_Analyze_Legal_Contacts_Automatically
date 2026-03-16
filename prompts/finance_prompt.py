from prompts.base_prompt import build_base_prompt

def finance_prompt(context: str):
    task = """
Analyze financial risks, payment terms, penalties,
indemnification, and cost exposures.

If legal findings indicate risks,
explain their financial impact.
"""
    return build_base_prompt("Financial Risk Analyst", task, context)