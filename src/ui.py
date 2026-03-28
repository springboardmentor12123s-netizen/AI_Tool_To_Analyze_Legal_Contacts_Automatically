import streamlit as st
import os
import tempfile
import sys
import concurrent.futures
import base64

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.document_utils import extract_text_from_pdf, create_documents_from_text
from src.pinecone_utils import PineconeManager
from src.clause_ai_graph import ClauseAIGraph

def display_pdf(file_bytes):
    base64_pdf = base64.b64encode(file_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def process_contract(uploaded_file, tone: str, structure: str, focus: str) -> dict:
    # Save uploaded file to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    
    try:
        # Ingest
        raw_text = extract_text_from_pdf(tmp_path)
        if not raw_text.strip():
            return {"error": "No text could be extracted from the PDF.", "file": uploaded_file.name}
        
        docs = create_documents_from_text(raw_text, uploaded_file.name)
        manager = PineconeManager()
        manager.add_documents(docs)
        
        # Run the Graph
        graph = ClauseAIGraph()
        query = "Perform a full multi-domain audit of this contract for risks and obligations."
        result = graph.run(query, tone=tone, structure=structure, focus=focus)
        result["file"] = uploaded_file.name
        return result
    except Exception as e:
        return {"error": f"An error occurred during analysis: {e}", "file": uploaded_file.name}
    finally:
        os.remove(tmp_path)

def main():
    st.set_page_config(page_title="AI Contract Analysis", layout="wide")

    st.title("📄 AI Contract Analysis Workflow")
    st.markdown("Upload contract(s) to perform a multi-domain audit across Legal, Finance, Compliance, and Operations using parallel AI agents.")

    with st.sidebar:
        st.header("⚙️ Customization Options")
        tone = st.selectbox("Tone", ["Professional", "Academic", "Direct"])
        structure = st.selectbox("Structure", ["Detailed Analysis", "High-level Summary"])
        focus = st.selectbox("Focus", ["All Domains", "Legal & Compliance Only", "Finance & Operations Only"])

    uploaded_files = st.file_uploader("Upload your Contract PDF(s) here", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        if st.button("Start Analysis", type="primary"):
            st.toast(f"Starting analysis for {len(uploaded_files)} document(s)...", icon="🚀")
            with st.status(f"Processing {len(uploaded_files)} document(s) concurrently...", expanded=True) as status:
                st.write("Extracting text and running multi-agent analysis...")
                results = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(uploaded_files), 5)) as executor:
                    futures = [executor.submit(process_contract, file, tone, structure, focus) for file in uploaded_files]
                    for future in concurrent.futures.as_completed(futures):
                        results.append(future.result())
                status.update(label="Analysis Complete!", state="complete", expanded=False)

            st.success("Analysis Complete!")
            
            tabs = st.tabs([res["file"] for res in results])
            for idx, tab in enumerate(tabs):
                with tab:
                    res = results[idx]
                    if "error" in res:
                        st.error(res["error"])
                    else:
                        col1, col2 = st.columns([1, 1], gap="large")
                        
                        file_bytes = None
                        for f in uploaded_files:
                            if f.name == res["file"]:
                                f.seek(0)
                                file_bytes = f.read()
                                break
                                
                        with col1:
                            st.subheader("📄 Document Preview")
                            if file_bytes:
                                display_pdf(file_bytes)
                                
                        with col2:
                            st.subheader("Final Audit Report")
                            
                            st.download_button(
                                label="⬇️ Download Markdown Report",
                                data=res["final_report"],
                                file_name=f"{res['file']}_Audit_Report.md",
                                mime="text/markdown",
                                key=f"download_{res['file']}"
                            )
                            
                            st.markdown(res["final_report"])
                            
                            st.feedback("thumbs", key=f"feedback_{res['file']}")

                            if "analysis_results" in res and res["analysis_results"]:
                                with st.expander("View Intermediate Domain Analysis"):
                                    for domain, content in res["analysis_results"].items():
                                        st.markdown(f"### {domain.upper()}")
                                        st.markdown(content)
                                        st.divider()

if __name__ == "__main__":
    main()
