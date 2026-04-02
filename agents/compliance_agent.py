from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.compliance_prompt import compliance_prompt



def analyze_compliance(contract_id:str,extra_context: str = ""):

    query = "GDPR data protection regulatory compliance audit requirements jurisdiction obligations"

    retrieved_context = retrieve_context(query, contract_id)

    # 🧠 Combine with Round 1 insights
    final_context = f"""
RETRIEVED CONTRACT CLAUSES:
{retrieved_context}

----------------------------------

CROSS-AGENT INSIGHTS:
{extra_context}
"""

    prompt = compliance_prompt(final_context)
    result = groq_chat(prompt, final_context)

    return {"analysis": result}