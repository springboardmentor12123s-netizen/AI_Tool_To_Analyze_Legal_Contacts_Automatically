# ClauseAI Environment Setup (Groq + Hugging Face Embeddings)

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
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Optional fallback providers
OPENAI_API_KEY=your_openai_key
LOCAL_LLM_URL=http://localhost:11434/api/chat
LOCAL_LLM_MODEL=llama3.1:8b
```

## 3) Provider options

- `CLAUSEAI_LLM_PROVIDER=groq` (default): fast remote inference with Groq.
- `CLAUSEAI_LLM_PROVIDER=ollama`: local Ollama inference.
- `CLAUSEAI_LLM_PROVIDER=openai`: OpenAI fallback.
- Retrieval uses local Hugging Face embeddings and an in-memory index per uploaded contract.

## 4) Run app

```bash
streamlit run app.py
```

## Notes

- If `GROQ_API_KEY` is missing and provider is `groq`, analysis will fail with a clear error.
- Multi-agent role analysis is enabled for Compliance, Finance, Legal, and Operations.
