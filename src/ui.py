import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="ClauseAI - Interactive Dashboard", layout="wide")

if "documents" not in st.session_state:
    st.session_state.documents = []
if "results" not in st.session_state:
    st.session_state.results = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None

st.title("ClauseAI 🤖⚖️")
st.subheader("Multi-Document Contract Analysis Dashboard")

# --- SIDEBAR: Config & Upload ---
with st.sidebar:
    st.header("1. Upload Documents")
    uploaded_files = st.file_uploader("Upload contracts", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    
    st.header("2. Report Configuration")
    tone = st.selectbox("Tone", ["formal", "concise", "executive"], index=0)
    structure = st.multiselect("Structure Sections", ["summary", "risks", "clauses", "recommendations"], default=["summary", "risks"])
    focus = st.multiselect("Focus Areas", ["liability", "payment_terms", "termination", "intellectual_property", "data_privacy"], default=["liability"])
    
    if st.button("Deep Extract & Analyze All"):
        if uploaded_files:
            with st.spinner("Uploading files..."):
                # Upload all files
                upload_data = [("files", (f.name, f, f.type)) for f in uploaded_files]
                upload_resp = requests.post(f"{API_URL}/upload_bulk", files=upload_data)
                
                if upload_resp.status_code == 200:
                    st.success(f"Uploaded {len(uploaded_files)} files.")
                    st.session_state.documents = [f.name for f in uploaded_files]
                    
                    with st.spinner("Analyzing all documents in parallel..."):
                        req_payload = {
                            "filenames": st.session_state.documents,
                            "report_config": {
                                "tone": tone,
                                "structure": structure,
                                "focus": focus
                            }
                        }
                        analyze_resp = requests.post(f"{API_URL}/analyze_bulk", json=req_payload)
                        if analyze_resp.status_code == 200:
                            st.session_state.results = analyze_resp.json().get("results", [])
                            st.success("Analysis complete!")
                        else:
                            st.error(f"Analysis failed: {analyze_resp.text}")
                else:
                    st.error(f"Upload failed: {upload_resp.text}")
        else:
            st.warning("Please upload at least one document.")

st.write("---")

# --- MAIN DASHBOARD (3 Panels) ---
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.markdown("### Document List")
    if not st.session_state.documents:
        st.info("No documents uploaded yet.")
    else:
        for doc in st.session_state.documents:
            # Provide a way to select a document to view
            if st.button(f"📄 {doc}", key=f"btn_{doc}"):
                st.session_state.selected_doc = doc

with col2:
    st.markdown("### Analysis Status")
    if not st.session_state.results:
        st.info("Awaiting analysis...")
    else:
        for res in st.session_state.results:
            fname = res.get("filename", "Unknown")
            status = res.get("status", "unknown")
            if status == "success":
                st.success(f"**{fname}**: Completed ✓")
            else:
                st.error(f"**{fname}**: Failed ✗ ({res.get('error', '')})")

with col3:
    st.markdown("### Report & Feedback")
    if st.session_state.selected_doc:
        selected_res = next((r for r in st.session_state.results if r.get("filename") == st.session_state.selected_doc), None)
        if selected_res and selected_res.get("status") == "success":
            st.markdown(f"#### Report for {st.session_state.selected_doc}")
            report_text = selected_res.get("final_report", "No report generated.")
            
            # Simple simulation of sections since LLM returns full markdown
            # Display full report
            st.markdown(report_text)
            
            st.markdown("---")
            st.markdown("**Give Feedback on this Analysis**")
            feedback_rating = st.radio("Is this report accurate?", ["👍 Thumbs Up", "👎 Thumbs Down"], horizontal=True, key=f"rating_{st.session_state.selected_doc}")
            feedback_comment = st.text_input("Comments (Optional)", key=f"comment_{st.session_state.selected_doc}")
            
            if st.button("Submit Feedback", key=f"submit_{st.session_state.selected_doc}"):
                fb_payload = {
                    "filename": st.session_state.selected_doc,
                    "section": "overall",
                    "rating": "up" if "👍" in feedback_rating else "down",
                    "comment": feedback_comment
                }
                fb_resp = requests.post(f"{API_URL}/feedback", json=fb_payload)
                if fb_resp.status_code == 200:
                    st.success("Feedback submitted!")
                else:
                    st.error("Failed to submit feedback.")
                    
            with st.expander("View Raw Extracted JSON"):
                st.json(selected_res.get("extracted_data", {}))
                
        elif selected_res and selected_res.get("status") == "error":
            st.error("Cannot display report due to analysis error.")
        else:
            st.warning("Analysis not complete or not found for this document.")
    else:
        st.info("Select a document from the list to view its report.")

st.write("---")
st.subheader("💬 Chat with Document (RAG)")
if st.session_state.selected_doc:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about the selected document..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    chat_resp = requests.post(
                        f"{API_URL}/chat",
                        json={"query": prompt, "filename": st.session_state.selected_doc}
                    )
                    if chat_resp.status_code == 200:
                        response_data = chat_resp.json()
                        answer = response_data.get("answer", "No answer provided.")
                        sources_used = response_data.get("sources_used", False)
                        
                        st.markdown(answer)
                        if sources_used:
                            st.caption("✓ Context used")
                        else:
                            st.caption("⚠ General knowledge")
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        st.error("Chat failed.")
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.info("Select a document first to chat with it.")
