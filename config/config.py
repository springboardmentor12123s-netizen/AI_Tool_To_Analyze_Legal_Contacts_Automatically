import os
from dotenv import load_dotenv

# Load environment variables early so config values resolve consistently everywhere.
load_dotenv()

# Read provider/API settings from env so secrets stay out of source code.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
CLAUSEAI_LLM_PROVIDER = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "hf").lower()
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "clauseai-contracts")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "default")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
PINECONE_HOST = os.getenv("PINECONE_HOST")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
