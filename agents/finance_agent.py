from utils.groq_llm import groq_chat
from rag.retriever import retrieve_context
from prompts.finance_prompt import finance_prompt


def analyze_finance(contract_text):
    context = retrieve_context(
        "payment terms penalties liabilities financial risks",
        contract_text
    )

    prompt = finance_prompt(context)
    result = groq_chat(prompt)

    return {"analysis": result}