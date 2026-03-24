# ClauseAI - Contract Analysis Agent System

![Dashboard Screenshot](https://via.placeholder.com/800x400.png?text=ClauseAI+Dashboard)

ClauseAI is a multi-agent system designed to deeply analyze legal contracts. It accelerates diligence and mitigates risks by seamlessly orchestrating specialized domain agents (Compliance, Finance, Legal, Operations) to dissect and evaluate documents concurrently.

## Tech Stack
- **Frontend**: Next.js (React, TailwindCSS)
- **Backend API**: FastAPI (Python, Uvicorn)
- **Orchestration**: LangGraph (StateGraph, Parallel Workflows)
- **Vector Store & RAG**: Pinecone, HuggingFace Embeddings
- **LLM Engine**: Groq (Llama 3.3 70B Fast Inference)

## Documentation

For instructions on how to set up, operate, and extend this project, refer to the following guides:

1. [📌 Setup Guide](docs/SETUP.md) - Instructions for local deployment and API keys.
2. [🏗️ System Architecture](docs/ARCHITECTURE.md) - Deep dive into modules and pipeline data flows.
3. [🔌 API Reference](docs/API_REFERENCE.md) - Definitions for backend HTTP service routes.

## Test CLI Execution
You can easily test the background parallel extraction via script (uses `src/bulk_processor.py`):
```bash
python cli_test_milestone4.py
```
