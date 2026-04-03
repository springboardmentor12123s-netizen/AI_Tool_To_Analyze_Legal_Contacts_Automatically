import streamlit as st
import tempfile
import os
import time

from app.utils.document_loader import load_document
from app.utils.text_processing import chunk_text
from app.services.vector_store import store_chunks
from app.workflow.contract_graph import build_graph

NAMESPACE = "contracts"

st.set_page_config(page_title="Clause AI", layout="wide")

# ------------------ SIDEBAR ------------------
st.sidebar.title("Settings")

analysis_type = st.sidebar.selectbox(
    "Select Analysis Type",
    ["Full Analysis", "Risk Only", "Summary Only"]
)

show_chunks = st.sidebar.checkbox("Show Chunks", False)

# ------------------ HEADER ------------------
st.title("Clause AI - Contract Analyzer")
st.markdown("Upload a contract and get structured AI insights.")

# ------------------ FILE UPLOAD ------------------
uploaded_file = st.file_uploader(
    "Upload Document",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:

    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        file_path = tmp_file.name

    st.success("File uploaded successfully")

    # ------------------ PROGRESS ------------------
    progress = st.progress(0)
    status = st.empty()

    # Step 1: Load
    status.text("Loading document...")
    document_text = load_document(file_path)
    progress.progress(20)

    if isinstance(document_text, list):
        document_text = "\n".join(document_text)

    # Step 2: Chunking
    status.text("Chunking document...")
    chunks = chunk_text(document_text)
    progress.progress(40)

    st.info(f"Chunks created: {len(chunks)}")

    if show_chunks:
        with st.expander("View Chunks"):
            for i, chunk in enumerate(chunks[:10]):
                st.write(f"Chunk {i+1}:")
                st.code(chunk[:500])

    # Step 3: Store
    status.text("Storing in vector DB...")
    store_chunks(chunks, namespace=NAMESPACE)
    progress.progress(60)

    # Step 4: AI Analysis
    status.text("Running AI agents...")
    graph = build_graph()

    try:
        result = graph.invoke({})
        progress.progress(100)
        status.text("Analysis complete ")

    except Exception as e:
        st.error(f"Error during analysis: {e}")
        os.remove(file_path)
        st.stop()

    # ------------------ OUTPUT UI ------------------

    st.divider()
    st.header("Analysis Results")

    # Tabs for structured output
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Summary", "Risks", "Clauses", "Raw Output"]
    )

    # ---------- TAB 1: SUMMARY ----------
    with tab1:
        st.subheader("Summary")
        try:
            st.write(result.get("summary", "No summary available"))
        except:
            st.write(result)

    # ---------- TAB 2: RISKS ----------
    with tab2:
        st.subheader("Risk Analysis")
        risks = result.get("risks", [])
        if risks:
            for r in risks:
                st.warning(r)
        else:
            st.success("No major risks detected")

    # ---------- TAB 3: CLAUSES ----------
    with tab3:
        st.subheader("Important Clauses")
        clauses = result.get("clauses", [])
        if clauses:
            for c in clauses:
                st.info(c)
        else:
            st.write("No clauses extracted")

    # ---------- TAB 4: RAW ----------
    with tab4:
        st.subheader("Raw Output")
        st.json(result)

    # ------------------ DOWNLOAD ------------------
    st.divider()
    st.subheader("📥 Export Report")

    st.download_button(
        label="Download Report",
        data=str(result),
        file_name="contract_analysis.txt"
    )

    # Cleanup
    os.remove(file_path)

else:
    st.info("Upload a file to start analysis")