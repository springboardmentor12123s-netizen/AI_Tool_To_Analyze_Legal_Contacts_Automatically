from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.compliance_prompt import compliance_prompt


def analyze_compliance(contract_text):
    context = retrieve_context(
        "compliance regulations GDPR data protection obligations",
        contract_text
    )

    prompt = compliance_prompt(context)
    result = groq_chat(prompt)

    return {"analysis": result}