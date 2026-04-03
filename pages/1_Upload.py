import streamlit as st
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css
from utils.api import process_contract_stream

st.set_page_config(page_title="Upload & Configure", layout="wide", page_icon="📝")
inject_custom_css()

# --- HEADER ---
st.title("📝 Configure Analysis & Upload")
st.caption("Customize your AI analysis and upload contracts for multi-agent evaluation.")

# --- LAYOUT ---
col_config, col_upload = st.columns([1, 1.5], gap="large")

# ================= CONFIG PANEL =================
with col_config:
    st.markdown("#### 🛠️ Report Builder")

    with st.container(border=True):
        st.session_state.tone = st.radio(
            "Tone",
            ["Executive Summary", "Formal", "Simple"],
            index=["Executive Summary", "Formal", "Simple"].index(
                st.session_state.get("tone", "Executive Summary")
            )
        )

        st.session_state.focus = st.selectbox(
            "Focus Area",
            ["All Domains", "Legal", "Financial", "Compliance", "Operations"],
            index=["All Domains", "Legal", "Financial", "Compliance", "Operations"].index(
                st.session_state.get("focus", "All Domains")
            )
        )

        st.session_state.structure = st.selectbox(
            "Length",
            ["Concise bullet points", "Detailed Analysis"],
            index=["Concise bullet points", "Detailed Analysis"].index(
                st.session_state.get("structure", "Concise bullet points")
            )
        )

        st.divider()

        # --- LIVE SUMMARY ---
        st.markdown("### 📌 Current Settings")
        st.info(
            f"""
            **Tone:** {st.session_state.tone}  
            **Focus:** {st.session_state.focus}  
            **Length:** {st.session_state.structure}
            """
        )

# ================= UPLOAD PANEL =================
with col_upload:
    st.markdown("#### 📄 Upload Contracts")

    uploaded_files = st.file_uploader(
        "Upload Contract PDF(s)",
        type=["pdf"],
        accept_multiple_files=True
    )

    # --- FILE PREVIEW ---
    if uploaded_files:
        st.markdown("### 📂 Uploaded Files")

        for file in uploaded_files:
            st.success(f"📄 {file.name}")

        st.caption(f"Total Files: {len(uploaded_files)}")

# ================= ANALYSIS SECTION =================
if uploaded_files:

    st.markdown("### 🚀 Start Analysis")

    if st.button("Generate Smart Dashboard", type="primary", use_container_width=True):

        results = []

        # --- PROGRESS UI ---
        progress_container = st.container()

        with progress_container:
            st.markdown("### ⚡ AI Processing Pipeline")

            col1, col2, col3, col4 = st.columns(4)

            stat_parse = col1.info("⏳ Parsing")
            stat_agents = col2.info("⏳ Agents")
            stat_score = col3.info("⏳ Scoring")
            stat_done = col4.info("⏳ Finalizing")

            progress_bar = st.progress(0)

        # --- PROCESS FILES ---
        total_files = len(uploaded_files)

        for idx, file in enumerate(uploaded_files):

            file.seek(0)
            fbytes = file.read()

            # Step 1
            stat_parse.success(f"✔️ Parsed {file.name}")
            progress_bar.progress((idx + 1) / (total_files * 4))

            # Step 2
            stat_agents.info("⏳ Running AI Agents...")
            res = process_contract_stream(
                file,
                fbytes,
                st.session_state.tone,
                st.session_state.structure,
                st.session_state.focus
            )
            results.append(res)
            stat_agents.success("✔️ Agents Done")
            progress_bar.progress((idx + 2) / (total_files * 4))

            # Step 3
            stat_score.info("⏳ Generating Scores...")
            stat_score.success("✔️ Scores Ready")
            progress_bar.progress((idx + 3) / (total_files * 4))

        # Step 4
        stat_done.success("✔️ Dashboard Ready")
        progress_bar.progress(1.0)

        # Save results
        st.session_state["analysis_results"] = results

        st.success("✅ Analysis Complete!")

        # --- QUICK NAVIGATION ---
        st.markdown("### 👉 Next Steps")

        col_next1, col_next2 = st.columns(2)

        with col_next1:
            st.info("📜 Go to **Viewer Page** to explore contract highlights")

        with col_next2:
            st.info("📊 Go to **Analytics Page** for insights & graphs")