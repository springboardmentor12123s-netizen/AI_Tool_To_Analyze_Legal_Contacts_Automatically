import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="ClauseAI - Parallel Extractor", layout="wide")

# Initialize chat history early so it persists across reruns
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_file" not in st.session_state:
    st.session_state.current_file = None

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
                        
                        # Store current file in session state for Chat feature
                        st.session_state.current_file = uploaded_file.name
                        
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

st.write("---")
st.subheader("💬 Chat with Document")
st.info("Ask questions about the uploaded document. If the answer isn't in the document, ClauseAI will use its general knowledge.")

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Ask a question about the contract..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                chat_resp = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "query": prompt,
                        "filename": st.session_state.current_file
                    }
                )
                
                if chat_resp.status_code == 200:
                    response_data = chat_resp.json()
                    answer = response_data.get("answer", "No answer provided.")
                    sources_used = response_data.get("sources_used", False)
                    
                    st.markdown(answer)
                    if sources_used:
                        st.caption("✓ Answered using document context (RAG)")
                    else:
                        st.caption("⚠ Answered using general knowledge (Not found in document)")
                        
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"Chat failed: {chat_resp.text}")
            except Exception as e:
                st.error(f"Error connecting to Chat API: {e}")
