from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag.pinecone_store import get_vectorstore


def ingest_document(doc_id: str, text: str):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=50
    )

    docs = splitter.create_documents([text])

    # ----------------------------------------
    # ✅ Attach Rich Metadata
    # ----------------------------------------

    for i, doc in enumerate(docs):
        doc.metadata["contract_id"] = doc_id
        doc.metadata["chunk_id"] = i
        doc.metadata["source"] = "contract_upload"

    vectorstore = get_vectorstore()

    # ----------------------------------------
    # ⚠️ Optional: Prevent Duplicate Inserts
    # ----------------------------------------

    # If your vector DB supports deletion by metadata,
    # you can uncomment below:

    # vectorstore.delete(filter={"contract_id": doc_id})

    # ----------------------------------------
    # ✅ Store Documents
    # ----------------------------------------

    vectorstore.add_documents(docs)

    print(f"✅ Stored {len(docs)} chunks in Pinecone for contract {doc_id}")