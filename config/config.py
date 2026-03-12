import os
from dotenv import load_dotenv

# Load environment variables early so config values resolve consistently everywhere.
load_dotenv()

# Read provider/API settings from env so secrets stay out of source code.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
CLAUSEAI_LLM_PROVIDER = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "clauseai-contracts")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "default")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
