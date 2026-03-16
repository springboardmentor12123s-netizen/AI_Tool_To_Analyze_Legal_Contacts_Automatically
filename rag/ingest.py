from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag.pinecone_store import get_vectorstore

def ingest_document(doc_id: str, text: str):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=350,
        chunk_overlap=40
    )

    docs = splitter.create_documents([text])

    vectorstore = get_vectorstore()
    vectorstore._index.delete(delete_all=True)
    vectorstore.add_documents(docs)

    print(f"✅ Stored {len(docs)} chunks in Pinecone")