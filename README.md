# 📄 ClauseAI – Multi-Agent Contract Analyzer

ClauseAI is an AI-powered contract analysis system that uses multiple specialized agents to analyze legal agreements.
The system processes contracts and provides insights related to **legal risks, financial obligations, regulatory compliance, and operational concerns**.

The project uses a **multi-agent architecture with LangGraph**, **LLMs from Groq**, and **Retrieval Augmented Generation (RAG)** powered by **Pinecone**.

---

# 🚀 Features

* 📑 Upload contracts in **PDF, DOCX, or TXT**
* 🤖 Multi-agent contract analysis
* ⚖ Legal clause evaluation
* 💰 Financial risk identification
* 🛡 Regulatory compliance analysis
* ⚙ Operational risk detection
* 🔎 Retrieval Augmented Generation (RAG) using Pinecone
* 🌐 Interactive interface using Streamlit

---

# 🧠 System Architecture

ClauseAI uses a **multi-agent workflow** where specialized AI agents analyze different aspects of a contract.

### Agents

| Agent            | Responsibility                                               |
| ---------------- | ------------------------------------------------------------ |
| Legal Agent      | Identifies risky clauses, liabilities, and termination terms |
| Finance Agent    | Detects payment terms, penalties, and financial risks        |
| Compliance Agent | Checks regulatory issues such as GDPR or data protection     |
| Operations Agent | Evaluates operational risks and execution challenges         |

### Workflow

1. Contract is uploaded through the Streamlit interface.
2. The document is parsed and converted into text.
3. Text is chunked and stored in **Pinecone Vector Database**.
4. Agents retrieve relevant context using **RAG**.
5. **LangGraph** orchestrates multi-agent execution.
6. Each agent generates findings and risk analysis.
7. Results are displayed in the UI.

---

# 🏗 Project Structure

```
ClauseAI
│
├── agents
│   ├── legal_agent.py
│   ├── finance_agent.py
│   ├── compliance_agent.py
│   └── operations_agent.py
│
├── prompts
│   ├── base_prompt.py
│   ├── legal_prompt.py
│   ├── finance_prompt.py
│   ├── compliance_prompt.py
│   └── operations_prompt.py
│
├── planner
│   ├── langgraph_planner.py
│   └── planning_module.py
│
├── rag
│   ├── ingest.py
│   ├── retriever.py
│   ├── pinecone_store.py
│   └── store_intermediate.py
│
├── utils
│   ├── groq_llm.py
│   └── embeddings.py
│
├── parser.py
├── app.py
└── README.md
```

---

# ⚙️ Installation

### 1️⃣ Clone the repository

```
git clone <repository-url>
cd ClauseAI
```

---

### 2️⃣ Create virtual environment

```
python -m venv venv
```

Activate environment

Windows:

```
venv\Scripts\activate
```

---

### 3️⃣ Install dependencies

```
pip install -r requirements.txt
```

---

### 4️⃣ Setup environment variables

Create a `.env` file in the root directory:

```
PINECONE_API_KEY=your_pinecone_key
GROQ_API_KEY=your_groq_key
```

---

# ▶️ Running the Application

Start the Streamlit app:

```
streamlit run app.py
```

Then open the browser and upload a contract file.

---




