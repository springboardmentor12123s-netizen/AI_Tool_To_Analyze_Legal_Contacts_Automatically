import streamlit as st
from modules.document_loader import load_document
from modules.chunker import chunk_text
from modules.vector_store import store_chunks, retrieve_chunks
from graph.workflow import graph
from modules.clients import get_clients
import uuid
import json
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
import io

# -----------------------------
# PDF GENERATION
# -----------------------------
def generate_pdf(report_text):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    story = []

    for line in report_text.split("\n"):
        if line.strip() == "":
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph(line, styles["Normal"]))

    doc.build(story)

    buffer.seek(0)
    return buffer

# -----------------------------
# SESSION STATE
# -----------------------------
defaults = {
    "logged_in": False,
    "username": "",
    "vectors_created": False,
    "namespace": None,
    "analysis_done": False,
    "analysis_result": None,
    "chat_history": [],
    "document_loaded": False,
    "contract_text": ""
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# -----------------------------
# USER STORAGE
# -----------------------------
def load_users():
    if not os.path.exists("users.json"):
        return {}
    try:
        with open("users.json", "r") as f:
            data = f.read().strip()
            return json.loads(data) if data else {}
    except:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# -----------------------------
# AUTH
# -----------------------------
def signup():
    st.title("Signup")
    u = st.text_input("Username")
    e = st.text_input("Email")
    p = st.text_input("Password", type="password")

    if st.button("Create Account"):
        users = load_users()
        if u in users:
            st.error("User exists")
        else:
            users[u] = {"email": e, "password": p}
            save_users(users)
            st.success("Account created!")

def login():
    st.title("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        users = load_users()
        if u not in users:
            st.error("User not found")
        elif users[u]["password"] != p:
            st.error("Wrong password")
        else:
            st.session_state.logged_in = True
            st.session_state.username = u
            st.rerun()

mode = st.sidebar.radio("Select", ["Login", "Signup"])

if not st.session_state.logged_in:
    login() if mode == "Login" else signup()
    st.stop()

# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title="ClauseAI", layout="wide")

st.sidebar.markdown(f"👤 {st.session_state.username}")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

st.title("📄 ClauseAI - Contract Analyzer")

# -----------------------------
# FILE UPLOAD
# -----------------------------
uploaded_file = st.file_uploader(
    "Upload Contract",
    type=["pdf", "docx"],
    accept_multiple_files=False
)

# -----------------------------
# PROCESS DOCUMENT
# -----------------------------
if uploaded_file and not st.session_state.document_loaded:

    st.session_state.namespace = str(uuid.uuid4())
    st.session_state.chat_history = []
    st.session_state.analysis_done = False
    st.session_state.analysis_result = None

    with st.spinner("Processing document..."):
        contract_text = load_document(uploaded_file)

        chunks = chunk_text(contract_text)
        chunks = chunks[:20]

        store_chunks(chunks, st.session_state.namespace)

    st.session_state.document_loaded = True
    st.session_state.contract_text = contract_text

    st.success("Document processed!")

# -----------------------------
# RUN ANALYSIS
# -----------------------------
if st.session_state.document_loaded:

    if not st.session_state.analysis_done:

        if st.button("🚀 Run Analysis"):

            with st.spinner("Analyzing contract..."):

                result = graph.invoke({
                    "contract_text": st.session_state.contract_text,
                    "namespace": st.session_state.namespace
                })

            st.session_state.analysis_result = result
            st.session_state.analysis_done = True

    else:
        result = st.session_state.analysis_result

# -----------------------------
# SHOW RESULT + DOWNLOAD
# -----------------------------
if st.session_state.analysis_done and st.session_state.analysis_result:

    report_text = st.session_state.analysis_result.get("final_report", "")

    st.subheader("📊 Analysis Report")
    st.write(report_text)

    # -----------------------------
    # DOWNLOAD PDF (FIXED)
    # -----------------------------
    pdf_file = generate_pdf(report_text)

    st.download_button(
        label="📄 Download Report as PDF",
        data=pdf_file,
        file_name="contract_analysis.pdf",
        mime="application/pdf"
    )

# -----------------------------
# CHAT
# -----------------------------
if st.session_state.analysis_done and st.session_state.analysis_result:

    st.subheader("💬 Chat with Contract")

    for chat in st.session_state.chat_history:
        st.markdown(f"**👤 You:** {chat['q']}")
        st.markdown(f"**🤖 AI:** {chat['a']}")

    if len(st.session_state.chat_history) >= 5:
        st.warning("Chat limit reached (to save API quota)")
        st.stop()

    question = st.chat_input("Ask something about the contract...")

    if question:

        client, _ = get_clients()

        with st.spinner("Thinking..."):

            chunks = retrieve_chunks(
                question,
                st.session_state.namespace
            )

            context = "\n\n".join(chunks[:2])[:1200]

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"""
                Answer briefly in bullet points (max 5).

                Context:
                {context}

                Question:
                {question}
                """
            )

        st.session_state.chat_history.append({
            "q": question,
            "a": response.text
        })

        st.rerun()