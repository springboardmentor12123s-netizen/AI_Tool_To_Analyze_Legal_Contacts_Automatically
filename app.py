import streamlit as st


st.set_page_config(page_title="ClauseAI", layout="wide")

st.title("📄 ClauseAI - Multi-Agent Contract Analyzer")

uploaded_file = st.file_uploader(
    "Upload a contract",
    type=["pdf", "docx", "txt"]
)

from parser import parse_document
from rag.ingest import ingest_document
from planner.langgraph_planner import run_langgraph



if uploaded_file:
    # Save file temporarily
    with open(uploaded_file.name, "wb") as f:
        f.write(uploaded_file.read())

    st.success("✅ File uploaded successfully")

    # Parse document
    contract_text = parse_document(uploaded_file.name)

  

    # 🔥 Store in Pinecone
    with st.spinner("Indexing document into Pinecone..."):
        ingest_document("contract1", contract_text)

    st.success("✅ Document stored in vector DB")

  

    with st.spinner("Running AI multi-agent analysis..."):
        report = run_langgraph(contract_text)

    # Display results
    st.markdown(f"""
## 🤖 LangGraph Multi-Agent Analysis

### ⚖️ Legal
{report['legal_r2']}

---

### 💰 Finance
{report['finance_r2']}

---

### 🛡 Compliance
{report['compliance_r2']}

---

### ⚙️ Operations
{report['operations_r2']}
""")