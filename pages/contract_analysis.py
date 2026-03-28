import os
import re
import streamlit as st
import pdfplumber
from docx import Document
from dotenv import load_dotenv
from groq import Groq
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

from graph_workflow import create_workflow
from prompts import (
    BASE_SYSTEM_PROMPT,
    COMPLIANCE_PROMPT,
    LEGAL_PROMPT,
    FINANCE_PROMPT,
    OPERATIONS_PROMPT
)

from .report_generator import ReportGenerator
# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Contract Analysis", layout="wide")

st.sidebar.title("📂 Navigation")
st.sidebar.page_link("app.py", label="🏠 Home")
st.sidebar.page_link("pages/contract_analysis.py", label="📄 Analyze Contract")
st.sidebar.page_link("pages/report_viewer.py", label="📊 View Report")

# -----------------------------
# ENV
# -----------------------------
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("clauseai-index")

@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

embedding_model = load_model()

# -----------------------------
# HELPERS
# -----------------------------
def extract_text(file, file_type):
    if file_type == "pdf":
        with pdfplumber.open(file) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    else:
        doc = Document(file)
        return "\n".join([p.text for p in doc.paragraphs])

def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def chunk_text(text, size=800):
    return [text[i:i+size] for i in range(0, len(text), size)]

def store_chunks(chunks, doc_id):
    vectors = []
    for i, chunk in enumerate(chunks):
        emb = embedding_model.encode(chunk).tolist()
        vectors.append({
            "id": f"{doc_id}-{i}",
            "values": emb,
            "metadata": {"text": chunk, "document": doc_id}
        })
    index.upsert(vectors)

def retrieve(query, doc_id, k=3):
    vec = embedding_model.encode(query).tolist()
    res = index.query(vector=vec, top_k=k, include_metadata=True, filter={"document": doc_id})
    return "\n".join([m["metadata"]["text"] for m in res["matches"]])

def run_agent(prompt, text):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": BASE_SYSTEM_PROMPT + prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message.content

# -----------------------------
# GRAPH
# -----------------------------
graph = create_workflow(
    run_agent,
    COMPLIANCE_PROMPT,
    LEGAL_PROMPT,
    FINANCE_PROMPT,
    OPERATIONS_PROMPT
)

# -----------------------------
# UI
# -----------------------------
st.title("📄 Contract Analysis")

uploaded_file = st.file_uploader("Upload Contract", type=["pdf", "docx"])

# -----------------------------
# REPORT CUSTOMIZATION UI (NEW)
# -----------------------------
st.sidebar.header("⚙ Report Settings")

tone = st.sidebar.selectbox(
    "Tone",
    ["formal", "analytical", "simple", "executive"]
)

structure = st.sidebar.selectbox(
    "Structure",
    ["bullet", "paragraph", "summary"]
)

focus = st.sidebar.multiselect(
    "Focus Areas",
    ["compliance", "legal", "finance", "operations"],
    default=["compliance", "legal", "finance", "operations"]
)

# Save config
st.session_state["report_config"] = {
    "tone": tone,
    "structure": structure,
    "focus": focus
}

# -----------------------------
# MAIN FLOW
# -----------------------------
if uploaded_file:

    file_type = uploaded_file.name.split(".")[-1]
    text = clean_text(extract_text(uploaded_file, file_type))

    with st.expander("📄 Preview"):
        st.text_area("", text[:2000], height=200)

    doc_id = uploaded_file.name
    chunks = chunk_text(text)
    store_chunks(chunks, doc_id)

    if st.button("🚀 Run Analysis"):

        with st.spinner("Analyzing..."):

            # STEP 1: Multi-agent graph analysis
            result = graph.invoke({
                "compliance_text": retrieve("compliance", doc_id),
                "legal_text": retrieve("legal", doc_id),
                "finance_text": retrieve("finance", doc_id),
                "operations_text": retrieve("operations", doc_id)
            })

            st.session_state["analysis_result"] = result

            # STEP 2: REPORT GENERATION (NEW)
            report_engine = ReportGenerator(client.chat.completions.create)

            final_report = report_engine.build_report(
                result,
                st.session_state["report_config"]
            )

            st.session_state["final_report"] = final_report

        st.success("✅ Analysis + Report Generated!")

        # DEBUG (optional)
        st.write(final_report)

        # NAVIGATE
        st.switch_page("pages/report_viewer.py")