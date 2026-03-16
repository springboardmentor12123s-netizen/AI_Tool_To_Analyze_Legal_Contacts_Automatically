from prompts.base_prompt import build_base_prompt

def compliance_prompt(context: str):
    task = """
Analyze regulatory compliance issues, data protection risks,
and jurisdictional concerns.

Consider whether legal or financial findings create
any regulatory or compliance violations.
"""
    return build_base_prompt("Regulatory Compliance Expert", task, context)