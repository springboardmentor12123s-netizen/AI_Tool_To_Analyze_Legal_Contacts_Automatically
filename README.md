# Infosys AI Contract Analysis Workflow

This project is a multi-domain AI Contract Analysis application powered by LangGraph, Pinecone, and Streamlit. It uses parallel AI agents to audit contracts across Legal, Finance, Compliance, and Operations domains.

## Features
- **Concurrent Processing**: Upload and analyze multiple contract PDFs in parallel.
- **Customizable Analysis**: Adjust the report Tone (Professional, Academic, Direct), Structure (High-level Summary, Detailed Analysis), and Focus (All Domains, Legal & Compliance Only, Finance & Operations Only).
- **Multi-Agent Architecture**: Built with LangGraph, simulating a team of legal, finance, compliance, and operations experts working concurrently.
- **Interactive UI**: A sleek Streamlit interface displaying tabbed results, intermediate agent findings, and user feedback collection.

## Setup
1. Ensure you have Python installed.
2. Install dependencies (Streamlit, LangChain, Pinecone, LangGraph, etc.).
3. Set your environment variables in a `.env` file:
   - `GROQ_API_KEY`
   - `GOOGLE_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX_NAME`

## Usage
Run the application using Streamlit:
```bash
python -m streamlit run src/ui.py
```

Upload your PDF contracts, select your customization preferences in the left sidebar, and click **Start Analysis** to view the consolidated executive reports.
