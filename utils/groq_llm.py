from langchain_groq import ChatGroq

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.3
        )
    return _llm

def groq_chat(prompt: str) -> str:
    llm = get_llm()
    response = llm.invoke(prompt)
    return response.content