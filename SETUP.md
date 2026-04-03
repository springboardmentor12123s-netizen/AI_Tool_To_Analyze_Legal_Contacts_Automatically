# ClauseAI Environment Setup (Groq + Pinecone Vector Database)

## 1) Install dependencies

```bash
pip install -r requirements.txt
```

## 2) Configure environment variables

Set these in your `.env`:

```env
CLAUSEAI_LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.1-8b-instant

# Pinecone vector database
PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX=clauseai-contracts
PINECONE_NAMESPACE=default
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# Embeddings used for Pinecone indexing/querying
EMBEDDING_PROVIDER=hf
OPENAI_API_KEY=your_openai_key
EMBEDDING_MODEL=text-embedding-3-small

# Optional local embedding fallback when OpenAI embeddings are not configured
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Optional fallback providers
LOCAL_LLM_URL=http://localhost:11434/api/chat
LOCAL_LLM_MODEL=llama3.1:8b
```

## 3) Provider options

- `CLAUSEAI_LLM_PROVIDER=groq` (default): fast remote inference with Groq.
- `CLAUSEAI_LLM_PROVIDER=ollama`: local Ollama inference.
- `CLAUSEAI_LLM_PROVIDER=openai`: OpenAI fallback.
- `EMBEDDING_PROVIDER=hf` (default): local sentence-transformer embeddings, recommended when using Groq.
- `EMBEDDING_PROVIDER=openai`: use OpenAI embeddings if you explicitly want them.
- Retrieval now uses Pinecone when `PINECONE_API_KEY` and `PINECONE_INDEX` are configured.
- If Pinecone is unavailable, ClauseAI falls back to a local in-memory vector index so analysis still completes.

## 4) Run app

```bash
streamlit run app.py
```

## Notes

- If `GROQ_API_KEY` is missing and provider is `groq`, analysis will fail with a clear error.
- Multi-agent role analysis is enabled for Compliance, Finance, Legal, and Operations.
- Pinecone indexing is batched and retrieval uses server-side similarity search filtered by `doc_id` for faster lookups.
