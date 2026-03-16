from prompts.base_prompt import build_base_prompt

def operations_prompt(context: str):
    task = """
Analyze operational risks, delivery timelines,
execution challenges, and monitoring concerns.

Use the legal, financial, or compliance findings
to determine possible execution problems.
"""
    return build_base_prompt("Operations Risk Analyst", task, context)