import os
from typing import List
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_pinecone import PineconeVectorStore
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_core.documents import Document

load_dotenv()

def load_document(file_path: str) -> List[Document]:
    """Load a document from a file path (PDF or DOCX)."""
    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
        return loader.load()
    elif file_path.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
        return loader.load()
    else:
        raise ValueError(f"Unsupported file format: {file_path}")

def split_documents(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Split documents into chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)

def ingest_documents(file_paths: List[str], index_name: str = "clauseai"):
    """
    Load, split, and ingest documents into Pinecone.
    
    Args:
        file_paths: List of paths to files to ingest.
        index_name: Name of the Pinecone index.
    """
    all_splits = []
    for path in file_paths:
        if not os.path.exists(path):
            print(f"File not found: {path}, skipping.")
            continue
            
        print(f"Loading {path}...")
        try:
            docs = load_document(path)
            splits = split_documents(docs)
            all_splits.extend(splits)
            print(f"Loaded {len(docs)} docs, split into {len(splits)} chunks.")
        except Exception as e:
            print(f"Error loading {path}: {e}")

    if not all_splits:
        print("No documents to ingest.")
        return

    print("Initializing Pinecone VectorStore...")
    
    # Ensure OPENAI_API_KEY is set for embeddings
    if not os.getenv("OPENAI_API_KEY"):
         print("WARNING: OPENAI_API_KEY not found. Embeddings may fail.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    # Ingest
    print(f"Upserting {len(all_splits)} chunks to index '{index_name}'...")
    PineconeVectorStore.from_documents(
        documents=all_splits,
        embedding=embeddings,
        index_name=index_name
    )
    print("Ingestion complete.")

if __name__ == "__main__":
    # Example usage
    # Create a dummy file if needed or point to existing ones
    # ingest_documents(["./data/sample_contract.pdf"])
    pass
