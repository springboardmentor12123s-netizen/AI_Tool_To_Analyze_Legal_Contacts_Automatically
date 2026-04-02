import streamlit as st
import uuid

# Core modules
from utils.parallel_processor import process_multiple_contracts
from parser import parse_document
from rag.ingest import ingest_document
from rag.qa import answer_contract_question_chat

# Reporting
from reporting.report_generator import generate_final_report
from reporting.pdf_generator import generate_pdf_report

# Caching
from utils.cache import (
    generate_cache_key,
    get_cached_report,
    save_cached_report,
    get_cached_pdf,
    save_cached_pdf,
    generate_qa_cache_key,
    get_cached_qa,
    save_cached_qa
)

# ----------------------------------------
# ⚙️ PAGE CONFIG
# ----------------------------------------

st.set_page_config(page_title="ClauseAI", layout="wide")

# ----------------------------------------
# 🎨 PROFESSIONAL UI
# ----------------------------------------

st.markdown("""
<style>

/* Background */
.stApp {
    background: #020617;
    color: #e5e7eb;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #020617;
    border-right: 1px solid #1f2937;
}

/* Cards */
.card {
    background: #020617;
    border: 1px solid #1f2937;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
}

/* Chat */
.user-msg {
    background: #1f2937;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 10px;
}

.ai-msg {
    background: #065f46;
    padding: 12px;
    border-radius: 12px;
    margin-bottom: 15px;
}

/* Buttons */
.stButton button {
    border-radius: 10px;
    height: 40px;
    background: linear-gradient(135deg, #22c55e, #16a34a);
    color: white;
}

/* Text */
h1, h2, h3 {
    color: #f8fafc;
}

hr {
    border: 1px solid #1f2937;
}

</style>
""", unsafe_allow_html=True)

# ----------------------------------------
# 🧠 HEADER
# ----------------------------------------

st.markdown("""
<h1>📄 ClauseAI</h1>
<p style='color:#9ca3af;'>AI-powered Contract Intelligence Platform</p>
<hr>
""", unsafe_allow_html=True)

# ----------------------------------------
# 📂 SIDEBAR
# ----------------------------------------

with st.sidebar:
    st.markdown("## 📂 Upload Contracts")

    uploaded_files = st.file_uploader(
        "Upload",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    st.markdown("## ⚙️ Settings")

    tone = st.selectbox("Tone", ["professional", "concise", "detailed"])
    focus = st.selectbox("Focus", ["balanced", "risk-heavy", "financial", "compliance"])

# ----------------------------------------
# 🧠 SESSION STATE
# ----------------------------------------

defaults = {
    "uploaded_files": set(),
    "analysis_results": None,
    "contract_map": {},
    "chat_history": {},
    "last_uploaded": None
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ----------------------------------------
# 🚀 PROCESSING
# ----------------------------------------

if uploaded_files:

    current_files = tuple([f.name for f in uploaded_files])

    if st.session_state.last_uploaded != current_files:
        st.session_state.analysis_results = None
        st.session_state.contract_map = {}
        st.session_state.chat_history = {}
        st.session_state.last_uploaded = current_files

    # ------------------------------
    # 📥 PARSE + INGEST
    # ------------------------------

    if not st.session_state.contract_map:

        contract_map = {}

        with st.spinner("📥 Processing contracts..."):
            for file in uploaded_files:

                contract_id = str(uuid.uuid4())

                with open(file.name, "wb") as f:
                    f.write(file.read())

                text = parse_document(file.name)

                if file.name not in st.session_state.uploaded_files:
                    ingest_document(contract_id, text)
                    st.session_state.uploaded_files.add(file.name)

                contract_map[contract_id] = {
                    "text": text,
                    "name": file.name
                }

        st.session_state.contract_map = contract_map

    contract_map = st.session_state.contract_map
    st.success(f"✅ {len(contract_map)} contracts ready")

    # ------------------------------
    # ⚡ AI ANALYSIS (RUN ONCE)
    # ------------------------------

    if not st.session_state.analysis_results:

        with st.spinner("⚡ Running AI analysis..."):
            results = process_multiple_contracts({
                cid: data["text"] for cid, data in contract_map.items()
            })

        st.session_state.analysis_results = results

    results = st.session_state.analysis_results

    # ------------------------------
    # 🔍 COL LAYOUT
    # ------------------------------

    col_main, col_chat = st.columns([3, 1])

    # ==============================
    # 📊 MAIN (REPORTS)
    # ==============================

    with col_main:

        st.markdown("## 📄 Contract Reports")

        all_reports = {}

        for cid, result in results.items():
            if result["status"] == "error":
                st.error(result["error"])
                continue
            all_reports[cid] = result["data"]

        if not all_reports:
            st.warning("No reports generated")
            st.stop()

        # ----------------------------------
        # 🎨 PROFESSIONAL REPORT RENDERING
        # ----------------------------------

        def format_section(title, content):
            return f"""
            <div style="margin-top:20px;">
                <h3 style="color:#f8fafc; border-left:4px solid #22c55e; padding-left:10px;">
                    {title}
                </h3>
                <div style="color:#d1d5db; line-height:1.6; margin-top:10px;">
                    {content}
                </div>
            </div>
            """

        def highlight_risks(text):
            text = text.replace("Critical:", "<span style='color:#ef4444; font-weight:bold;'>Critical:</span>")
            text = text.replace("High:", "<span style='color:#f97316; font-weight:bold;'>High:</span>")
            text = text.replace("Medium:", "<span style='color:#eab308; font-weight:bold;'>Medium:</span>")
            text = text.replace("Low:", "<span style='color:#22c55e; font-weight:bold;'>Low:</span>")
            return text

        # ----------------------------------
        # 📊 RENDER EACH CONTRACT
        # ----------------------------------

        for cid, report in all_reports.items():

            file_name = contract_map[cid]["name"]

            combined = (
                report["legal_r2"]
                + report["finance_r2"]
                + report["compliance_r2"]
                + report["operations_r2"]
            )

            key = generate_cache_key(combined, tone, focus)

            final_report = get_cached_report(key)

            if not final_report:
                final_report = generate_final_report(report, tone, focus, file_name)
                save_cached_report(key, final_report)

            # 🔥 CLEAN SECTION SPLIT (important)
            sections = final_report.split("🔍")

            formatted_report = f"""
            <div style="
                background:#020617;
                padding:25px;
                border-radius:16px;
                border:1px solid #1f2937;
                margin-bottom:30px;
            ">
                <h2 style="color:#22c55e;">📄 {file_name}</h2>
                <hr style="border:1px solid #1f2937;">
            """

            for sec in sections:
                sec = highlight_risks(sec.strip())
                if sec:
                    formatted_report += f"<div style='margin-bottom:15px;'>{sec}</div>"

            formatted_report += "</div>"

            st.markdown(formatted_report, unsafe_allow_html=True)

            # ----------------------------------
            # 📄 BETTER PDF DOWNLOAD
            # ----------------------------------

            pdf = get_cached_pdf(key)

            if not pdf:
                pdf = generate_pdf_report(final_report, file_name)
                pdf = save_cached_pdf(key, pdf)

            with open(pdf, "rb") as f:
                st.download_button(
                    "📄 Download Professional PDF",
                    f,
                    file_name=f"{file_name}.pdf",
                    use_container_width=True
                )

    # ==============================
    # 💬 CHAT PANEL
    # ==============================

    with col_chat:

        st.markdown("## 💬 Chat")

        labels = {contract_map[cid]["name"]: cid for cid in all_reports}

        selected = st.selectbox("Contract", list(labels.keys()))
        cid = labels[selected]

        if cid not in st.session_state.chat_history:
            st.session_state.chat_history[cid] = []

        chat = st.session_state.chat_history[cid]

        for q, a in chat:
            st.markdown(f'<div class="user-msg">🧑 {q}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="ai-msg">🤖 {a}</div>', unsafe_allow_html=True)

        q = st.text_input("Ask something...")

        col1, col2 = st.columns(2)

        send = col1.button("Send")
        clear = col2.button("Clear")

        if clear:
            st.session_state.chat_history[cid] = []
            st.rerun()

        if send and q.strip():

            key = generate_qa_cache_key(q, cid)
            ans = get_cached_qa(key)

            if not ans:
                with st.spinner("Thinking..."):
                    ans = answer_contract_question_chat(q, cid, chat)
                save_cached_qa(key, ans)

            chat.append((q, ans))
            st.rerun()