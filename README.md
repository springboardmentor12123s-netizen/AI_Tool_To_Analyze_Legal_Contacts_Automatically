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

### Run Experiment
To run a sample contract analysis:
```bash
python experiment.py
```
This script will:
1. Create a sample contract (`sample_contract.txt`).
2. Ingest it into Pinecone.
3. specific agents query Pinecone for relevant clauses.
4. Print the analysis from each agent.

### Run Tests
```bash
python -m pytest tests/
```

## Project Structure
- `src/agent_graph.py`: LangGraph definition and agent logic.
- `src/ingest.py`: Document loading and Pinecone ingestion.
- `tests/`: Unit tests.
- `experiment.py`: Main script for running contract analysis experiments.
- `requirements.txt`: Python dependencies.

## OUTPUT
Risk Analysis Results
Compliance Analysis
COMPLIANCE RISK 1
Clause: 2.C
Risk Type: Contract Termination
Risk Level: High
Recommendation: Review and revise the termination clause to ensure it aligns with industry standards and provides adequate notice to the Consultant.

COMPLIANCE RISK 2
Clause: 2.F
Risk Type: Payment Delay
Risk Type: Risk Level: Medium
Recommendation: Clarify the payment approval process to ensure timely payments and avoid delays.

COMPLIANCE RISK 3
Clause: 2.H
Risk Type: Invoicing and Reimbursement
Risk Level: Medium
Recommendation: Review and revise the invoicing requirements to ensure compliance with industry standards and reduce the risk of reimbursement disputes.
Legal Analysis
LEGAL RISK 1
Clause: 2.C
Risk Type: Contract Termination
Risk Level: High
Recommendation: Review and revise the termination clause to ensure it aligns with industry standards and provides adequate notice to the Consultant.

LEGAL RISK 2
Clause: 2.F
Risk Type: Payment Delay
Risk Level: Medium
Recommendation: Clarify the payment approval process to ensure timely payments and avoid delays.

LEGAL RISK 3
Clause: 2.H
Risk Type: Invoicing and Reimbursement
Risk Level: Medium
Recommendation: Review and revise the invoicing requirements to ensure compliance with industry standards and reduce the risk of reimbursement disputes.
Finance Analysis
FINANCIAL RISK 1
Clause: 2.C
Risk Type: Contract Termination
Risk Level: High
Recommendation: Review and revise the termination clause to ensure it aligns with industry standards and provides adequate notice to the Consultant.

FINANCIAL RISK 2
Clause: 2.F
Risk Type: Payment Delay
Risk Level: Medium
Recommendation: Clarify the payment approval process to ensure timely payments and avoid delays.

FINANCIAL RISK 3
Clause: 2.H
Risk Type: Invoicing and Reimbursement
Risk Level: Medium
Recommendation: Review and revise the invoicing requirements to ensure compliance with industry standards and reduce the risk of reimbursement disputes.
Operations Analysis
OPERATIONS RISK 1
Clause: 2.C
Risk Type: Contract Termination
Risk Level: High
Recommendation: Review and revise the termination clause to ensure it aligns with industry standards and provides adequate notice to the Consultant.

OPERATIONS RISK 2
Clause: 2.F
Risk Type: Payment Delay
Risk Level: Medium
Recommendation: Clarify the payment approval process to ensure timely payments and avoid delays.

OPERATIONS RISK 3
Clause: 2.H
Risk Type: Invoicing and Reimbursement
Risk Level: Medium
Recommendation: Review and revise the invoicing requirements to ensure compliance with industry standards and reduce the risk of reimbursement disputes.