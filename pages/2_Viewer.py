import streamlit as st
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css, highlight_text

st.set_page_config(page_title="Contract Viewer", layout="wide", page_icon="📄")
inject_custom_css()

st.title("📄 Interactive Contract Viewer")
st.caption("Explore contract clauses with AI-powered highlighting and explainability.")

# --- CHECK DATA ---
if "analysis_results" not in st.session_state or not st.session_state.analysis_results:
    st.warning("No contracts analyzed yet. Please go to the Upload page.")
    st.stop()

results = st.session_state.analysis_results

# --- SELECT CONTRACT ---
if len(results) > 1:
    selected_idx = st.selectbox(
        "📂 Select Contract",
        range(len(results)),
        format_func=lambda x: results[x]["file"]
    )
    res = results[selected_idx]
else:
    res = results[0]
    st.markdown(f"**Viewing:** {res.get('file', 'Unknown Document')}")

if "error" in res:
    st.error(res["error"])
    st.stop()

# --- FETCH RISKS ---
risks = res.get("metrics", {}).get("risks", []) if res.get("metrics") else []

# ================= TOP SUMMARY =================
if risks:
    total = len(risks)
    high = len([r for r in risks if r.get("severity", 0) >= 8])
    medium = len([r for r in risks if 5 <= r.get("severity", 0) < 8])
    low = len([r for r in risks if r.get("severity", 0) < 5])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Issues", total)
    col2.metric("High Risk", high)
    col3.metric("Medium Risk", medium)
    col4.metric("Low Risk", low)

    st.divider()

# ================= FILTERS =================
col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    selected_severity = st.multiselect(
        "Filter by Risk Level",
        ["High", "Medium", "Low"],
        default=["High", "Medium", "Low"]
    )

with col_filter2:
    detected_domains = []
    for r in risks:
        dom = r.get("domain", "Unknown").title()
        if dom == "Finance": dom = "Financial"
        detected_domains.append(dom)
        
    all_options = list(set(["Legal", "Financial", "Compliance", "Operations"] + detected_domains))

    selected_domain = st.multiselect(
        "Filter by Domain",
        all_options,
        default=all_options
    )

# Apply filters
def filter_risks(r):
    sev = r.get("severity", 0)
    level = "High" if sev >= 8 else "Medium" if sev >= 5 else "Low"
    dom = r.get("domain", "Unknown").title()
    if dom == "Finance": dom = "Financial"
    return level in selected_severity and dom in selected_domain

filtered_risks = [r for r in risks if filter_risks(r)]

# ================= SEARCH =================
search_query = st.text_input("🔍 Search inside contract")

raw_text = res.get("raw_text", "")

if search_query:
    raw_text = raw_text.replace(
        search_query,
        f"<mark style='background-color: #93c5fd'>{search_query}</mark>"
    )

# ================= MAIN LAYOUT =================
col_text, col_insights = st.columns([2, 1], gap="large")

# ---------- CONTRACT VIEW ----------
with col_text:
    st.subheader("📜 Source Contract")
    st.caption("Hover over highlighted text to see AI insights.")

    html_view = highlight_text(raw_text, filtered_risks)
    st.markdown(html_view, unsafe_allow_html=True)

# ---------- INSIGHTS PANEL ----------
with col_insights:
    st.subheader("🤖 Key Insights")

    if selected_domain:
        for domain in selected_domain:
            st.markdown(f"#### {domain} Insights")
            
            domain_risks = [
                r for r in filtered_risks 
                if r.get("domain", "Unknown").title().replace("Finance", "Financial") == domain
            ]
            
            if domain_risks:
                for idx, risk in enumerate(domain_risks):
                    sev = risk.get('severity', 0)
                    icon = "🔴" if sev >= 8 else "🟡" if sev >= 5 else "🟢"

                    with st.container(border=True):
                        st.markdown(
                            f"**{icon} {risk.get('domain', '').capitalize()} Risk**  \n{risk.get('risk')}"
                        )

                        # --- QUICK INFO ---
                        st.caption(f"Severity: {sev} | Probability: {risk.get('probability', 'N/A')}")

                        # --- JUMP BUTTON (UX BOOST) ---
                        btn_key = f"btn_{domain}_{idx}"
                        if st.button("📍 Highlight Clause", key=btn_key):
                            st.info("Scroll the contract to locate highlighted clause.")

                        # --- EXPLAINABLE AI ---
                        with st.expander("🧠 Explain this analysis"):
                            conf_score = int(risk.get('confidence_score', 0))

                            st.progress(
                                conf_score / 100.0,
                                text=f"Confidence Score: {conf_score}/100"
                            )

                            st.markdown("**📝 Source Quote:**")
                            st.info(f"*{risk.get('quote', 'N/A')}*")

                            st.markdown("**🧠 Reasoning Pathway:**")
                            for idx_step, step in enumerate(risk.get('reasoning_steps', [])):
                                st.caption(f"Step {idx_step+1}: {step}")
            else:
                st.info(f"No risks match the filters for {domain}.")
    else:
        st.success("No domains selected.")