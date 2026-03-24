# ClauseAI Architecture

## Source Code Directory (`src/`)

| File / Folder              | Role / Description                                                                 |
|----------------------------|------------------------------------------------------------------------------------|
| **`agent_graph.py`**       | Orchestrator workflow using LangGraph; manages StateGraph transitions.             |
| **`api.py`**               | FastAPI backend server routing HTTP requests to the components.                    |
| **`bulk_processor.py`**    | Concurrent handler for multi-document scaling using `asyncio` semaphores.          |
| **`ingest.py`**            | Handles document parsing and text loading via LangChain loaders.                   |
| **`parallel_extractor.py`**| Executes various domain agents in parallel to speed up extraction.                 |
| **`pinecone_store.py`**    | Manages vector database ingestion and semantic retrieval for the Chat bot.         |
| **`prompts.py`**           | Prompts template definitions for different domain extraction agents.               |
| **`report_generator.py`**  | Crafts final structured markdown reports applying user configuration overrides.    |
| **`ui.py`**                | Alternate/legacy Streamlit UI version for simple local visualization.              |
| **`pipelines/`**           | Sub-directory containing domain-specific LLM extractions (Compliance, Finance).    |

## Pipeline Flow

1. **PDF Upload**: Documents securely uploaded via frontend to the FastAPI `/upload_bulk` endpoint.
2. **Chunking**: Text loaded and segmented into candidate clauses using LangChain splitters.
3. **Parallel Extraction**: The chunked clauses are farmed out to multiple domain LLM extractors concurrently.
4. **Pinecone Storage**: Evaluated risks, text, and metadata are embedded and saved to Pinecone.
5. **Report Synthesis**: The report generator queries the data and generates the final configured report.
6. **UI Display**: The Next.js dashboard processes the response and presents a multi-panel interactive experience.
