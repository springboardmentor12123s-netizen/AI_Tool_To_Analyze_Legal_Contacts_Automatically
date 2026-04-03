import streamlit as st
import os
import tempfile
import sys
import concurrent.futures
import json
import re
import pandas as pd
import plotly.express as px

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.document_utils import extract_text_from_pdf, create_documents_from_text
from src.pinecone_utils import PineconeManager
from src.clause_ai_graph import ClauseAIGraph
from src.config import get_llm, get_pinecone_index, get_embeddings
from langchain_core.prompts import ChatPromptTemplate

# --- Feature 9: Design Pass & Glassmorphism ---
def inject_custom_css():
    st.markdown("""
    <style>
    /* Ultra Modern Minimalist Theme */
    :root {
      --primary: #0f172a;
      --secondary: #3b82f6;
      --surface: #ffffff;
      --text-main: #334155;
      --bg-color: #f8fafc;
    }
    
    /* Global Background */
    .stApp {
        background-color: var(--bg-color);
        color: var(--text-main);
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.6) !important;
    }

    /* Card Styling */
    .css-1r6slb0, .st-emotion-cache-1wivap2, .st-emotion-cache-1c7y2kd {
        border-radius: 16px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
        background-color: var(--surface);
        border: 1px solid #e2e8f0;
    }

    /* KPI Cards */
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem;
        color: var(--primary);
        font-weight: 800;
        letter-spacing: -1px;
    }

    /* Contract Text Viewer Container */
    .contract-viewer {
        background: white;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        height: 75vh;
        overflow-y: auto;
        font-family: 'Georgia', serif;
        line-height: 1.8;
        color: #1e293b;
        box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.03);
    }
    
    /* Sleek buttons */
    .stButton>button {
        border-radius: 8px !important;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    </style>
    """, unsafe_allow_html=True)


# --- Feature 1: Smart Risk HTML Highlighter ---
def highlight_text(raw_text, risks):
    html_text = raw_text.replace('\n', '<br><br>')
    for r in risks:
        quote = r.get("quote", "")
        if quote and len(quote) > 10 and quote != "exact text from contract if available":
            # Determine color by severity mapping
            sev = r.get("severity", 0)
            if sev >= 8:
                color, border = "rgba(239,68,68,0.2)", "#dc2626" # Red
            elif sev >= 5:
                color, border = "rgba(234,179,8,0.2)", "#ca8a04" # Yellow
            else:
                color, border = "rgba(34,197,94,0.2)", "#16a34a" # Green
                
            reasoning = " | ".join(r.get("reasoning_steps", []))
            # Create hover tooltip tag
            tag = f'<mark style="background-color: {color}; border-bottom: 2px solid {border}; padding: 2px 4px; border-radius: 4px; cursor: help; color: #0f172a;" title="AI INSIGHT: {r.get("risk")} \nREASONING: {reasoning}">{quote}</mark>'
            
            # Simple replace to avoid regex breaking on weird characters
            html_text = html_text.replace(quote, tag)
            
    return f'<div class="contract-viewer">{html_text}</div>'


def extract_json_metrics(report_text):
    try:
        match = re.search(r'```json\s*(.*?)\s*```', report_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except: pass
    return None


def process_contract_stream(uploaded_file, file_bytes, tone, structure, focus):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        raw_text = extract_text_from_pdf(tmp_path)
        if not raw_text.strip():
            return {"error": "No text extracted.", "file": uploaded_file.name}
            
        docs = create_documents_from_text(raw_text, uploaded_file.name)
        PineconeManager().add_documents(docs)
        
        # Execute workflow
        graph = ClauseAIGraph()
        query = "Perform a full multi-domain audit of this contract for risks and obligations."
        final_state = graph.run(query, tone=tone, structure=structure, focus=focus)
        
        result = final_state
        result["file"] = uploaded_file.name
        result["raw_text"] = raw_text
        
        metrics = extract_json_metrics(result.get("final_report", ""))
        if metrics:
            result["metrics"] = metrics
            result["final_report"] = re.sub(r'```json.*?```', '', result["final_report"], flags=re.DOTALL).strip()
            
        return result
    except Exception as e:
        return {"error": str(e), "file": uploaded_file.name}
    finally:
        try: os.remove(tmp_path)
        except: pass


def main():
    st.set_page_config(page_title="Smart Contract Dashboard", layout="wide", page_icon="⚡")
    inject_custom_css()

    # Top hero section
    col_hero1, col_hero2 = st.columns([3, 1])
    with col_hero1:
        st.title("⚡ Smart Contract Dashboard")
        st.markdown("Upload your contracts, customize your report, and get AI-powered insights instantly.")
    with col_hero2:
        try:
            st.image("/home/kanika/Desktop/projects/infosys/web_network_illustration.png", use_container_width=True)
        except Exception:
            pass

    # Sidebar for Chat only
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Scale_of_justice_2.svg/1200px-Scale_of_justice_2.svg.png", width=50)
        st.header("🔍 Ask Your Portfolio")
        st.info("Mini-ChatGPT explicitly grounded in your uploaded contracts.")
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
            
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if prompt_text := st.chat_input("E.g., What are the penalties for late payment?"):
            st.session_state.chat_history.append({"role": "user", "content": prompt_text})
            with st.chat_message("user"):
                st.markdown(prompt_text)
                
            with st.chat_message("assistant"):
                with st.spinner("Searching contracts..."):
                    try:
                        emb = get_embeddings().embed_query(prompt_text)
                        hits = get_pinecone_index().query(vector=emb, top_k=5, include_metadata=True, namespace="default")
                        context_texts = [m["metadata"]["text"] for m in hits.get("matches", []) if "text" in m["metadata"]]
                        ctx = "\n---\n".join(context_texts)
                        if not ctx:
                            ans_txt = "No relevant clauses found in the vector database."
                        else:
                            sys_p = "You are an AI Legal Assistant. Answer the user based ONLY on these exact contract extracts:\n\n{context}"
                            chat_p = ChatPromptTemplate.from_messages([("system", sys_p), ("human", "{question}")])
                            ans_txt = (chat_p | get_llm()).invoke({"context": ctx, "question": prompt_text}).content
                    except Exception as e:
                        ans_txt = f"Search failed: {e}"
                        
                st.markdown(ans_txt)
            st.session_state.chat_history.append({"role": "assistant", "content": ans_txt})

    # --- Main Area ---
    st.markdown("### 📝 1. Configure Analysis & Upload")
    
    col_upload, col_config = st.columns([1.5, 1], gap="large")
    
    with col_config:
        st.markdown("#### 🛠️ Report Builder")
        with st.container(border=True):
            tone = st.radio("Tone", ["Executive Summary", "Formal", "Simple"], index=0)
            focus = st.selectbox("Focus Area", ["All Domains", "Legal", "Financial", "Compliance"])
            structure = st.selectbox("Length", ["Concise bullet points", "Detailed Analysis"])

    with col_upload:
        st.markdown("#### 📄 Documents")
        uploaded_files = st.file_uploader("Upload Contract PDF(s)", type=["pdf"], accept_multiple_files=True)

    if uploaded_files:
        if st.button("Generate Smart Dashboard", type="primary", use_container_width=True):
            results = []
            
            # --- Feature 8: Real-Time Processing Feedback ---
            progress_container = st.empty()
            with progress_container.container():
                st.markdown("### ⚡ AI Pipeline Status")
                col1, col2, col3, col4 = st.columns(4)
                stat_parse = col1.info("⏳ Parsing PDFs...")
                stat_legal = col2.empty()
                stat_fin = col3.empty()
                stat_score = col4.empty()
                
            # Execute synchronously to show steps visually (or simulate)
            for file in uploaded_files:
                file.seek(0)
                fbytes = file.read()
                
                stat_parse.success(f"✔️ Parsed {file.name}")
                stat_legal.info("⏳ Agents Analyzing...")
                
                # Processing backend
                res = process_contract_stream(file, fbytes, tone, structure, focus)
                results.append(res)
                
                stat_legal.success("✔️ Analysis Complete")
                stat_fin.info("⏳ Generating JSON Scorecards...")
                
            stat_fin.success("✔️ Scorecards Ready")
            stat_score.success("✔️ Dashboard Launched!")
            
            # Collapse status
            progress_container.empty()
            
            # Save to session_state
            st.session_state["analysis_results"] = results
            
        # Natively check session state to prevent app reload disappearing act
        if "analysis_results" in st.session_state:
            results = st.session_state["analysis_results"]
            
            if len(results) > 0:
                tab_names = ["📈 Multi-Agent Analytics"] + [res["file"] for res in results]
                tabs = st.tabs(tab_names)
                
                # --- Feature 3: Multi-Agent Conversation Viewer (Analytics) ---
                with tabs[0]:
    st.title("📈 Multi-Agent Analytics Dashboard")

    all_risks = []
    for res in results:
        if "metrics" in res and res.get("metrics") and res["metrics"].get("risks"):
            for r in res["metrics"]["risks"]:
                r["file"] = res["file"]
                all_risks.append(r)

    if all_risks:
        df_risks = pd.DataFrame(all_risks)

        # --- DATA PREPROCESSING ---
        df_risks["risk_level"] = df_risks["severity"].apply(
            lambda x: "High" if x >= 8 else "Medium" if x >= 5 else "Low"
        )

        # --- KPI METRICS ---
        st.subheader("📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Risks", len(df_risks))
        col2.metric("High Risk", len(df_risks[df_risks["severity"] >= 8]))
        col3.metric("Avg Severity", round(df_risks["severity"].mean(), 2))
        col4.metric("Avg Probability", round(df_risks["probability"].mean(), 2))

        st.divider()

        # --- ROW 1: PIE + DOMAIN BAR ---
        colA, colB = st.columns(2)

        with colA:
            severity_counts = df_risks["risk_level"].value_counts().reset_index()
            severity_counts.columns = ["Risk Level", "Count"]

            fig_pie = px.pie(
                severity_counts,
                names="Risk Level",
                values="Count",
                title="Overall Risk Distribution",
                color="Risk Level",
                color_discrete_map={
                    "High": "#ef4444",
                    "Medium": "#eab308",
                    "Low": "#22c55e"
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with colB:
            domain_score = df_risks.groupby("domain")["severity"].mean().reset_index()

            fig_domain = px.bar(
                domain_score,
                x="domain",
                y="severity",
                title="Average Risk Score per Domain",
                color="severity",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig_domain, use_container_width=True)

        # --- ROW 2: STACKED BAR + SCATTER ---
        colC, colD = st.columns(2)

        with colC:
            stacked_data = df_risks.groupby(
                ["domain", "risk_level"]
            ).size().reset_index(name="count")

            fig_stack = px.bar(
                stacked_data,
                x="domain",
                y="count",
                color="risk_level",
                title="Risk Breakdown per Domain",
                barmode="stack",
                color_discrete_map={
                    "High": "#ef4444",
                    "Medium": "#eab308",
                    "Low": "#22c55e"
                }
            )
            st.plotly_chart(fig_stack, use_container_width=True)

        with colD:
            fig_scatter = px.scatter(
                df_risks,
                x="probability",
                y="severity",
                color="domain",
                size="confidence_score",
                hover_data=["risk", "file"],
                title="Severity vs Probability Matrix",
                size_max=25
            )
            fig_scatter.update_layout(
                xaxis=dict(range=[0, 11]),
                yaxis=dict(range=[0, 11])
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- ROW 3: HEATMAP ---
        st.subheader("🔥 Risk Heatmap")

        heatmap_data = df_risks.pivot_table(
            index="domain",
            columns="file",
            values="severity",
            aggfunc="mean"
        )

        fig_heat = px.imshow(
            heatmap_data,
            text_auto=True,
            aspect="auto",
            title="Risk Heatmap (Domain vs Contract)",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # --- INSIGHTS PANEL ---
        st.subheader("🧠 Key Insights")

        highest_domain = domain_score.sort_values(
            by="severity", ascending=False
        ).iloc[0]

        lowest_domain = domain_score.sort_values(
            by="severity"
        ).iloc[0]

        st.error(f"🔴 Highest Risk Domain: {highest_domain['domain']}")
        st.success(f"🟢 Safest Domain: {lowest_domain['domain']}")
        st.info(f"📊 Total Contracts Analyzed: {df_risks['file'].nunique()}")

    else:
        st.info("No structured risks were extracted across the portfolio.")

if __name__ == "__main__":
    main()
