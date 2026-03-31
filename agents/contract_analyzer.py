from modules.vector_store import retrieve_chunks
from modules.clients import get_clients

def analyze_contract(contract_text, namespace):

    client, _ = get_clients()

    question = "Summarize important risks and key points from this contract"

    chunks = retrieve_chunks(question, namespace)
    context = "\n\n".join(chunks[:3])[:1500]

    prompt = f"""
    You are an expert contract analyst.

    Analyze the contract and return ONLY key points in this format:

    COMPLIANCE:
    - point
    - point

    FINANCE:
    - point
    - point

    LEGAL:
    - point
    - point

    OPERATIONS:
    - point
    - point

    RULES:
    - Max 5 points per section
    - Each point = 1 short sentence
    - No explanations
    - No paragraphs

    Context:
    {context}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text