from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.finance_prompt import finance_prompt


def analyze_finance(contract_id:str,extra_context: str = ""):

    query = "payment schedule penalties late fees indemnity cost exposure financial risk pricing terms"

    retrieved_context = retrieve_context(query, contract_id)

    # 🧠 Combine with Round 1 insights
    final_context = f"""
RETRIEVED CONTRACT CLAUSES:
{retrieved_context}

----------------------------------

CROSS-AGENT INSIGHTS:
{extra_context}
"""

    prompt = finance_prompt(final_context)
    result = groq_chat(prompt, final_context)

    return {"analysis": result}