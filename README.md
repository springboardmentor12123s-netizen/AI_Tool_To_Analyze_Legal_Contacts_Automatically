# ClauseAI - Contract Analysis Agent System

ClauseAI is a multi-agent system designed to analyze legal contracts. It uses **LangGraph** to orchestrate four specialized agents (Compliance, Finance, Legal, Operations) and **Pinecone** for Retrieval-Augmented Generation (RAG).

## Features
- **Multi-Agent Architecture**: Specialized agents for different domains.
- **RAG Integration**: Retrieves relevant contract clauses using Pinecone and HuggingFace embeddings.
- **Document Support**: Parses PDF, DOCX, and TXT files.
- **Local Embeddings**: Uses `all-MiniLM-L6-v2` (no OpenAI key required for embeddings).
- **LLM**: Powered by Groq (Llama 3.3 70B).

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repo-url>
    cd clauseai
    ```

2.  **Install dependencies**:
    ```bash
    # Create virtual environment
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Install packages
    pip install -r requirements.txt
    ```

3.  **Environment Variables**:
    Create a `.env` file with:
    ```bash
    GROQ_API_KEY=your_groq_key
    PINECONE_API_KEY=your_pinecone_key
    ```
    *Note: `OPENAI_API_KEY` is NOT required.*

4.  **Initialize Pinecone Index**:
    Run the setup script to create the `clauseai` index:
    ```bash
    python setup_pinecone.py
    ```

## Usage

### 1. Start Support Services
Required for both API and UI.
```bash
# Start the Backend API
uvicorn src.api:app --reload --port 8000
```

### 2. User Interface (Streamlit)
The easiest way to use ClauseAI.
```bash
streamlit run src/ui.py
```
Upload a PDF/DOCX, and the system will:
1.  Ingest it into Pinecone.
2.  Classify the contract type (NDA, MSA, etc.).
3.  Coordinate specific agents to analyze it.
4.  Display the results.


### 4. Run Tests
```bash
python -m pytest tests/
```

## Project Structure
- `src/agent_graph.py`: LangGraph definition and agent logic.
- `src/ingest.py`: Document loading and Pinecone ingestion.
- `tests/`: Unit tests.
- `requirements.txt`: Python dependencies.

