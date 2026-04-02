from prompts.base_prompt import build_base_prompt

def compliance_prompt(context: str):
    task = """
Identify regulatory compliance risks and data protection issues
ONLY if explicitly mentioned or inferable from context.
"""
    return build_base_prompt("Compliance Expert", task, context)