from rag.retriever import retrieve_context
from utils.groq_llm import groq_chat


def answer_contract_question_chat(question, contract_id, chat_history):

    # 🔍 Retrieve context
    context = retrieve_context(question, contract_id, top_k=5)

    # 🧠 Chat memory
    history_text = ""
    for q, a in chat_history[-5:]:
        history_text += f"Q: {q}\nA: {a}\n"

    prompt = f"""
You are a senior legal contract analyst.

STRICT RULES:
- Answer ONLY using the provided context
- Do NOT use external knowledge
- If answer not found → say "Not mentioned in contract"

Conversation History:
{history_text}

---------------------
CONTEXT:
{context}
---------------------

QUESTION:
{question}

ANSWER:
"""

    return groq_chat(prompt, context)