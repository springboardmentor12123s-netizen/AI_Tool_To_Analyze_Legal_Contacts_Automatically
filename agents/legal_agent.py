from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.legal_prompt import legal_prompt


def analyze_legal(contract_text):
    context = retrieve_context(
        "legal risks termination liability clauses",
        contract_text
    )

    prompt = legal_prompt(context)
    result = groq_chat(prompt)

    return {"analysis": result}