
from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.operations_prompt import operations_prompt


def analyze_operations(contract_text):
    context = retrieve_context(
        "delivery timelines service obligations operational risks",
        contract_text
    )

    prompt = operations_prompt(context)
    result = groq_chat(prompt)

    return {"analysis": result}