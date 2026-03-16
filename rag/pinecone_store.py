import os
from dotenv import load_dotenv

load_dotenv()
from langchain_pinecone import PineconeVectorStore
from utils.embeddings import get_embeddings

INDEX_NAME = "clauseai-rag"

def get_vectorstore():
    return PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=get_embeddings(),
        pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    )