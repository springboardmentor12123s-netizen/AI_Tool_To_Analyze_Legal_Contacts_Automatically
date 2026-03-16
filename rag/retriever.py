from rag.pinecone_store import get_vectorstore


def retrieve_context(query: str, contract_text: str, top_k=3):
    enhanced_query = f"{query}\n\nCONTRACT SUMMARY:\n{contract_text[:500]}"

    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})

    docs = retriever.invoke(enhanced_query)

    return "\n".join([d.page_content for d in docs])

   