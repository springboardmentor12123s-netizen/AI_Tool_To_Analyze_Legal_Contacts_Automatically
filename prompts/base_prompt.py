from langchain_core.prompts import PromptTemplate

def build_base_prompt(role: str, task: str, context: str):

    template = """
You are a {role} analyzing a contract.

CRITICAL INSTRUCTIONS (STRICT):
- Use ONLY the provided context
- Do NOT assume, infer, or add external knowledge
- If information is NOT present → DO NOT mention it
- Do NOT invent locations, laws, or entities
- Stay STRICTLY within your domain

DOMAIN RESTRICTION:
- Legal → clauses, liability, termination
- Finance → payment, penalties, cost ONLY
- Compliance → regulations ONLY if explicitly mentioned
- Operations → execution, delivery ONLY

FORMAT RULES (VERY STRICT):
- ONLY 3 sections: Findings, Risks, Advice
- NO other headings allowed
- Bullet points must start with "-"
- Each bullet must be ONE short line
- NO paragraphs

SECTION-SPECIFIC RULES (STRICT):

Findings:
- MUST contain EXACTLY 3 bullet points
- DO NOT exceed or reduce

Risks:
- MUST contain between 2 and 5 bullet points ONLY
- Include ONLY important risks from context
- Order by importance (critical first)
- If no risks → write "- None"

Advice:
- MUST contain EXACTLY 3 bullet points
- DO NOT exceed or reduce

CRITICAL:
- Do NOT apply "2 to 5" rule to Findings or Advice
- Each section must follow ONLY its own rule

CONTEXT:
{context}

TASK:
{task}

OUTPUT FORMAT (STRICTLY FOLLOW):

Findings:
- ...
- ...
- ...

Risks:
- ...
- ...
- ...

Advice:
- ...
- ...
- ...
"""

    prompt = PromptTemplate.from_template(template)

    return prompt.format(
        role=role,
        task=task,
        context=context
    )