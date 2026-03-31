from modules.vector_store import retrieve_chunks
from modules.clients import get_clients

def operations_agent(contract_text, namespace):

    client, _ = get_clients()

    question = "Check operational risks, regulatory issues, and policy violations."

    chunks = retrieve_chunks(question, namespace)
    context = "\n\n".join(chunks)

    prompt = f"""
You are a Compliance Expert.

Give ONLY key compliance risks in bullet points.

Rules:
- Maximum 5–7 points
- Each point must be 1 short sentence
- No paragraphs, no explanations
- Be concise and direct

Focus on:
- Regulatory risks
- Missing clauses
- Policy violations

Context:
{context}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text