# ClauseAI

ClauseAI is a multi-agent contract intelligence system built to analyze legal agreements, surface business and legal risks, and generate structured professional reports from uploaded documents.

The system accepts `PDF`, `DOCX`, and `TXT` contracts, breaks analysis across specialist AI roles, applies retrieval-enhanced reasoning when available, and returns a clean reviewer-friendly output instead of a plain text summary.

## What This Project Does

ClauseAI is designed for contract review workflows where users need more than a generic summary. It helps identify:

- important clauses and obligations
- legal, financial, compliance, and operational risks
- missing protections or weak drafting
- practical follow-up actions
- a polished final report for download and sharing

The core idea is simple: one model response is often too shallow for serious contract review, so ClauseAI distributes the analysis across multiple specialist agents and then consolidates the result into a structured output.

## Why ClauseAI Stands Out

- Multi-agent reasoning instead of a single generic summary pass
- Clause-aware contract analysis with role-based perspectives
- Retrieval-augmented analysis using embeddings and Pinecone when configured
- Batch processing for multiple contracts in one run
- Professional report generation in both `PDF` and `DOCX`
- Configurable output tone, structure, and focus area
- Streamlit-based interactive UI with document preview, analysis tabs, and downloadable reports

## Core Capabilities

### 1. Multi-Agent Contract Review

ClauseAI runs specialist analysis across these perspectives:

- `Legal`
- `Finance`
- `Compliance`
- `Operations`

Each agent focuses on a distinct review angle, helping the system surface different classes of risk and obligations before producing the final consolidated result.

### 2. Clause-Level Insight

The system extracts and organizes key clauses and highlights why they matter in the context of the agreement.

### 3. Risk Detection

ClauseAI identifies:

- critical issues
- missing or weak protections
- contract-specific risk signals
- practical recommendations for follow-up

### 4. Report Generation

After analysis, the app produces a structured report with sections such as:

- Executive Summary
- Overall Risk Rating
- Critical Issues
- Key Obligations
- Missing Protections / Negotiation Gaps
- Recommended Actions
- Conclusion

Reports can be downloaded as `PDF` and `DOCX`.

### 5. Batch Processing

The app supports analyzing multiple uploaded contracts in one workflow, with per-file status tracking and per-document report output.

### 6. Retrieval-Augmented Analysis

When Pinecone and embeddings are configured, ClauseAI indexes contract chunks and retrieves contextual evidence during analysis. If Pinecone is not available, the system falls back to local or in-memory retrieval behavior so the app can still run.

## End-to-End Workflow

1. A user uploads a contract in `PDF`, `DOCX`, or `TXT` format.
2. The document loader extracts and normalizes the text.
3. The analyzer identifies contract signals and prepares role-specific context.
4. Specialist agents review the contract from multiple perspectives.
5. The system synthesizes the results into structured analysis.
6. The report generator produces a professional final report.
7. The UI presents previews, agent-by-agent analysis, risk summaries, and export options.

## System Architecture

### `app.py`

The Streamlit frontend and workflow controller.

Responsibilities:

- file upload handling
- analysis mode selection
- batch and comparison flows
- report viewing and export
- feedback capture
- rendering risk widgets and report sections

### `core/document_loader.py`

Handles document ingestion and parsing.

Responsibilities:

- loading `PDF`, `DOCX`, and `TXT`
- extracting page text
- basic document normalization
- chunking content for retrieval and indexing

### `core/clause_analyzer.py`

The main analysis engine.

Responsibilities:

- contract-type-aware analysis flow
- multi-agent orchestration
- clause extraction
- structured synthesis
- output cleanup and normalization
- progress-stage updates for the UI

### `core/llm_engine.py`

The language-model and retrieval integration layer.

Responsibilities:

- LLM calls
- Groq and OpenAI-compatible interaction
- optional local-model fallback
- embeddings
- Pinecone indexing and retrieval
- cached artifact storage and retrieval

### `core/report_generator.py`

Builds the polished report output.

Responsibilities:

- generating formal report sections
- preparing metadata
- creating downloadable `DOCX`
- creating downloadable `PDF`

### `core/batch_processor.py`

Runs multi-document analysis and returns ordered results for the UI.

## Tech Stack

This README is aligned to the actual project dependencies and implementation.

- Python
- Streamlit
- LangChain
- LangGraph
- OpenAI-compatible API client
- Groq API integration
- Pinecone vector database
- Sentence Transformers
- `pypdf`
- `python-docx`
- `python-dotenv`
- `reportlab`

## AI / Retrieval Stack

ClauseAI currently supports:

- `Groq` as the default remote LLM provider
- `OpenAI` as a supported provider
- optional local model usage through provider switching
- `Pinecone` for vector retrieval
- `sentence-transformers/all-MiniLM-L6-v2` as the default local embedding model
- OpenAI embeddings when configured

## Project Features in the Current Build

- Single-contract analysis
- Multi-contract comparison
- Batch upload and processing
- Agent-by-agent analysis tabs
- Structured final report generation
- Risk overview UI
- Downloadable `PDF` report
- Downloadable `DOCX` report
- Local feedback logging
- Session-persisted analysis results inside the UI

## Repository Structure

```text
ClauseAI/
|-- app.py
|-- requirements.txt
|-- SETUP.md
|-- assets/
|-- config/
|   |-- __init__.py
|   `-- config.py
|-- core/
|   |-- __init__.py
|   |-- batch_processor.py
|   |-- clause_analyzer.py
|   |-- document_loader.py
|   |-- llm_engine.py
|   |-- planning_module.py
|   `-- report_generator.py
|-- data/
|   `-- report_feedback.jsonl
|-- src/
|   |-- __init__.py
|   |-- agent_graph.py
|   |-- agents.py
|   |-- app.py
|   |-- graph.py
|   |-- ingest.py
|   `-- rag_pipeline.py
|-- tests/
|   |-- __init__.py
|   |-- test_agents.py
|   `-- test_ingest.py
`-- utils/
    |-- __init__.py
    `-- prompts.py
```

## Installation

From the project root:

```bash
pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file and configure the values you need:

```env
CLAUSEAI_LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.1-8b-instant

PINECONE_API_KEY=your_pinecone_key
PINECONE_INDEX=clauseai-contracts
PINECONE_NAMESPACE=default
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

EMBEDDING_PROVIDER=hf
OPENAI_API_KEY=your_openai_key
EMBEDDING_MODEL=text-embedding-3-small
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Important notes:

- `CLAUSEAI_LLM_PROVIDER=groq` is the default configuration.
- `CLAUSEAI_LLM_PROVIDER=openai` is supported.
- Pinecone is optional but improves retrieval quality.
- If Pinecone is unavailable, the app can still run with fallback retrieval behavior.

## Running the App

Run from the project root:

```bash
streamlit run app.py
```

## Output Generated by ClauseAI

Users can inspect:

- structured analysis output
- agent-by-agent specialist analysis
- key risks and follow-up actions
- generated professional report
- downloadable `PDF` and `DOCX` files

## Evaluation Summary

ClauseAI is not just a document summarizer. It is a modular contract intelligence pipeline that combines:

- multi-agent reasoning
- retrieval-enhanced context handling
- clause-focused analysis
- report generation
- batch-capable document processing
- an evaluator-friendly interactive UI

It demonstrates applied AI engineering across orchestration, document understanding, retrieval, interface design, and production-style output generation.

## Notes

- Feedback submissions are stored locally in `data/report_feedback.jsonl`.
- PDF export uses the project code and prefers `reportlab` when available.
- The project currently supports `PDF`, `DOCX`, and `TXT` uploads.
