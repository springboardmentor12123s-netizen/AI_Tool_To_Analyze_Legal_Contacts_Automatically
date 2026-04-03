# src/config.py
import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from pinecone import Pinecone

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "default-index")
    
    # Use the current stable Llama 3.1 model
    LLM_MODEL = "llama-3.1-8b-instant" 
    # Use the mainline Gemini embedding model
    EMBEDDING_MODEL = "models/gemini-embedding-001" 

def get_embeddings():
    # Force the stable 'v1' API version to avoid deprecation errors
    return GoogleGenerativeAIEmbeddings(
        model=Config.EMBEDDING_MODEL,
        google_api_key=Config.GOOGLE_API_KEY,
        version="v1",
        # Force 768 dimensions to match your existing Pinecone Index
        output_dimensionality=768 
    )

def get_llm():
    # Groq provides high-speed inference for these models
    return ChatGroq(
        temperature=0.1, 
        groq_api_key=Config.GROQ_API_KEY, 
        model_name=Config.LLM_MODEL
    )
def get_pinecone_index():
    pc = Pinecone(api_key=Config.PINECONE_API_KEY)
    return pc.Index(Config.PINECONE_INDEX_NAME)