from langchain_core.prompts import PromptTemplate


def build_base_prompt(role: str, task: str, context: str):

    template = """
You are a {role} in a multi-agent contract analysis system.

Your job is to analyze the contract using ONLY the information in the context.

Important Rules:
- Do NOT guess or invent information.
- Only reference other agents if their findings appear in the context.
- Do NOT create agents like "Agent 1", "Agent 2".
- If no prior findings are available, analyze the contract independently.
- Keep answers short and clear (max 2-3 points per section).

Context:
{context}

Task:
{task}

Return output exactly in this format:

Findings:
- ...

Risks:
- ...

Advice:
- ...
"""

    prompt = PromptTemplate.from_template(template)

    return prompt.format(
        role=role,
        task=task,
        context=context
    )