import streamlit as st

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="ClauseAI",
    layout="wide",
    page_icon="📄"
)

# =====================================================
# SIDEBAR NAVIGATION
# =====================================================
st.sidebar.title("📂 Navigation")

st.sidebar.page_link("app.py", label="🏠 Home")
st.sidebar.page_link("pages/contract_analysis.py", label="📄 Analyze Contract")
st.sidebar.page_link("pages/report_viewer.py", label="📊 View Report")

st.sidebar.divider()

st.sidebar.info("ClauseAI - Multi-Agent Contract Intelligence System")

# =====================================================
# MAIN LANDING PAGE
# =====================================================

st.title("📄 ClauseAI - Contract Intelligence Platform")

st.markdown("""
Welcome to **ClauseAI**, an AI-powered platform that analyzes contracts using a multi-agent system.

---

### 🚀 What You Can Do

- ⚖ **Compliance Analysis**  
  Detect regulatory and confidentiality risks  

- 📜 **Legal Risk Detection**  
  Identify liabilities, IP issues, and legal gaps  

- 💰 **Financial Insights**  
  Analyze payment terms, penalties, and obligations  

- ⚙ **Operational Review**  
  Evaluate delivery timelines and feasibility  

---

### 🧠 How It Works

1. Upload your contract  
2. AI agents analyze different domains  
3. Results are combined into a professional report  

---

👉 Use the sidebar to start analyzing your contract.
""")

# =====================================================
# FEATURE HIGHLIGHTS (COLUMNS)
# =====================================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Compliance", "✔", "Monitored")

with col2:
    st.metric("Legal", "✔", "Analyzed")

with col3:
    st.metric("Financial", "✔", "Evaluated")

with col4:
    st.metric("Operations", "✔", "Reviewed")

st.divider()

# =====================================================
# CALL TO ACTION
# =====================================================
st.subheader("🚀 Get Started")

st.info("Upload a contract and generate a detailed AI-powered analysis report.")

if st.button("📄 Start Contract Analysis", use_container_width=True):
    st.switch_page("pages/contract_analysis.py")

# =====================================================
# FOOTER
# =====================================================
st.divider()

st.caption("© 2026 ClauseAI | Built with Streamlit, LangGraph, and Pinecone")