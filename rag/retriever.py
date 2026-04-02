from rag.pinecone_store import get_vectorstore


def retrieve_context(query: str, contract_id: str, top_k=5):

    vectorstore = get_vectorstore()

    search_kwargs = {
        "k": top_k,
        "filter": {"contract_id": contract_id}
    }

    retriever = vectorstore.as_retriever(search_kwargs=search_kwargs)

    docs = retriever.invoke(query)

    if not docs:
        return "No relevant clauses found in this contract."

    return "\n\n".join([d.page_content for d in docs])