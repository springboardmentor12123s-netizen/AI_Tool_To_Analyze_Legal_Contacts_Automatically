from rag.pinecone_store import get_vectorstore


def store_agent_result(agent_name: str, contract_id: str, analysis: str):
    """
    Store intermediate agent analysis into Pinecone
    """

    vectorstore = get_vectorstore()

    metadata = {
        "agent": agent_name,
        "contract_id": contract_id
    }

    vectorstore.add_texts(
        texts=[analysis],
        metadatas=[metadata]
    )