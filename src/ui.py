import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="ClauseAI - Parallel Extractor", layout="wide")

st.title("ClauseAI 🤖⚖️")
st.subheader("Parallel Processing & Multi-Domain Contract Analysis")

with st.sidebar:
    st.info("Upload a contract. The system will extract clauses in parallel and generate a final report.")
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])

if uploaded_file is not None:
    st.write("---")
    st.write(f"**File:** {uploaded_file.name}")
    
    if st.button("Deep Extract & Analyze"):
        with st.spinner("Uploading and analyzing (this may take a moment)..."):
            try:
                # 1. Upload File
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                upload_resp = requests.post(f"{API_URL}/upload", files=files)
                
                if upload_resp.status_code != 200:
                    st.error(f"Upload failed: {upload_resp.text}")
                else:
                    st.success("File uploaded. Starting parallel extraction...")
                    
                    # 2. Analyze
                    analyze_resp = requests.post(
                        f"{API_URL}/analyze", 
                        json={"filename": uploaded_file.name}
                    )
                    
                    if analyze_resp.status_code == 200:
                        data = analyze_resp.json()
                        final_report = data.get("final_report", "")
                        extracted_data = data.get("extracted_data", {})
                        
                        st.success("Analysis Complete!")
                        
                        st.markdown("### 📝 Executive Synthesis Report")
                        st.markdown(final_report)
                        
                        st.markdown("---")
                        st.markdown("### 🔍 Raw Extracted Findings (JSON)")
                        with st.expander("View Structured Extraction Data"):
                            st.json(extracted_data)
                                    
                    else:
                        st.error(f"Analysis failed: {analyze_resp.text}")
                        
            except Exception as e:
                st.error(f"Error connecting to API: {e}")
                st.warning("Make sure the backend API is running.")
