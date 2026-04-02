
from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.operations_prompt import operations_prompt


def analyze_operations(contract_id:str,extra_context: str = ""):

    query = "delivery timeline SLA service levels execution delays dependencies operational risk"

    retrieved_context = retrieve_context(query, contract_id)

    # 🧠 Combine with Round 1 insights
    final_context = f"""
RETRIEVED CONTRACT CLAUSES:
{retrieved_context}

----------------------------------

CROSS-AGENT INSIGHTS:
{extra_context}
"""

    prompt = operations_prompt(final_context)
    result = groq_chat(prompt, final_context)

    return {"analysis": result}