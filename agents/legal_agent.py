from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.legal_prompt import legal_prompt



def analyze_legal(contract_id:str,extra_context: str = ""):

    query = "termination clauses breach liability indemnity dispute resolution jurisdiction risk"

    retrieved_context = retrieve_context(query, contract_id)

    # 🧠 Combine with Round 1 insights
    final_context = f"""
RETRIEVED CONTRACT CLAUSES:
{retrieved_context}

----------------------------------

CROSS-AGENT INSIGHTS:
{extra_context}
"""

    prompt = legal_prompt(final_context)
    result = groq_chat(prompt, final_context)

    return {"analysis": result}