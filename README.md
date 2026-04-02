# 📄 ClauseAI – Multi-Agent Contract Intelligence Platform

ClauseAI is an advanced AI-powered system for analyzing legal contracts using a **multi-agent architecture**, **LangGraph orchestration**, and **Retrieval-Augmented Generation (RAG)**.

It provides deep insights into **legal risks, financial exposure, compliance obligations, and operational challenges**, along with **chat-based Q&A**, **caching**, and **professional PDF reports**.

---

# 🚀 Key Features

### 🤖 Multi-Agent AI Analysis

* Legal, Finance, Compliance, and Operations agents
* Parallel + multi-round reasoning using LangGraph

### 🔎 RAG with Pinecone

* Context-aware retrieval using vector search
* Contract-specific filtering using metadata

### 💬 Contract Chat (Q&A)

* Ask questions about contracts
* Context-aware answers with memory (chat history)

### ⚡ Smart Caching System

* LLM response caching
* Report caching
* PDF caching
* Q&A caching

### 📄 Professional PDF Reports

* Consulting-style structured reports
* Executive summary + insights
* Auto-generated downloadable PDFs

### 📂 Multi-Contract Support

* Upload multiple contracts
* Parallel processing using ThreadPoolExecutor

### 🎨 Production-Level UI

* Clean dark UI (Streamlit)
* Sidebar controls (tone, focus)
* Chat panel + reports panel

---

# 🧠 System Architecture

## 🔹 Multi-Agent Workflow

1. Contract uploaded
2. Parsed into text
3. Chunked & stored in Pinecone (with metadata)
4. Round 1 → Agents run in parallel
5. Intermediate results stored in vector DB
6. Round 2 → Agents refine using shared context
7. Final report generated
8. Chat + PDF enabled

---

## 🤖 Agents

| Agent         | Responsibility                  |
| ------------- | ------------------------------- |
| ⚖ Legal       | Clauses, liability, termination |
| 💰 Finance    | Payments, penalties, cost risks |
| 🛡 Compliance | Regulations, GDPR, obligations  |
| ⚙ Operations  | Delivery, execution, SLAs       |

---

## 🔁 LangGraph Flow

```
START
  ↓
[Legal R1]   [Finance R1]   [Compliance R1]   [Operations R1]
        ↓ (sync)
            ↓
[Legal R2]   [Finance R2]   [Compliance R2]   [Operations R2]
            ↓
           END
```

---

# 🏗 Project Structure

```
ClauseAI
│
├── agents/                # AI Agents
├── prompts/               # Prompt engineering
├── planner/               # LangGraph orchestration
├── rag/                   # Retrieval pipeline (Pinecone)
├── reporting/             # PDF + report generation
├── utils/                 # LLM, caching, embeddings
│
├── app.py                 # Streamlit UI
├── parser.py              # File parsing
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation

## 1️⃣ Clone Repo

```
git clone <your-repo-url>
cd ClauseAI
```

---

## 2️⃣ Create Virtual Environment

```
python -m venv venv
```

Activate:

```
venv\Scripts\activate
```

---

## 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

## 4️⃣ Setup Environment Variables

Create `.env` file:

```
PINECONE_API_KEY=your_key
GROQ_API_KEY=your_key
```

---

# ▶️ Run Application

```
streamlit run app.py
```

---

# 📊 How It Works (Deep Insight)

### 🔹 RAG Pipeline

* Contracts split into chunks
* Stored in Pinecone with metadata:

  * contract_id
  * chunk_id
* Retrieval uses strict filtering:

```
filter = {"contract_id": contract_id}
```

---

### 🔹 Multi-Round Reasoning

#### Round 1:

* Each agent analyzes contract independently

#### Round 2:

* Agents receive:

  * Legal findings
  * Finance findings
  * Compliance findings
  * Operations findings
* Produces refined insights

---

### 🔹 Caching Strategy

| Cache Type   | Purpose                  |
| ------------ | ------------------------ |
| LLM Cache    | Avoid repeated API calls |
| Report Cache | Faster UI                |
| PDF Cache    | Avoid regeneration       |
| Q&A Cache    | Instant answers          |

---

### 🔹 Chat System

* Uses RAG + history
* Keeps last 5 conversations
* Strict rule:

```
If not in contract → "Not mentioned in contract"
```

---

# 📄 PDF Report Features

* Cover page
* Executive summary
* Key insights
* Section-wise analysis
* Clean consulting format

---

# ⚡ Performance Optimizations

* Parallel processing (max_workers=2)
* Rate-limit handling (retry + backoff)
* LLM response caching
* Controlled API calls

---

# 🔐 Strict AI Controls

Your system enforces:

* ❌ No hallucinations
* ❌ No external knowledge
* ✅ Context-only answers
* ✅ Domain-specific reasoning
* ✅ Structured outputs

---

## 📜 License
This project is licensed under the MIT License.

