import streamlit as st
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css

st.set_page_config(page_title="Multi-Agent Analysis", layout="wide", page_icon="🧠")
inject_custom_css()

st.title("🧠 Multi-Agent Analysis")
st.caption("Detailed breakdown of contract risks identified by specialized AI agents.")

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
risks = res.get("metrics", {}).get("risks", [])

if not risks:
    st.success("No structured risks detected.")
    st.stop()

# ================= DOMAIN SUMMARY =================
st.subheader("📊 Domain Risk Overview")

domain_summary = {
    "Legal": {"count": 0, "severity_sum": 0},
    "Financial": {"count": 0, "severity_sum": 0},
    "Compliance": {"count": 0, "severity_sum": 0},
    "Operations": {"count": 0, "severity_sum": 0}
}

for r in risks:
    domain = r.get("domain", "Other").capitalize()
    if domain == "Finance":
        domain = "Financial"
        
    if domain not in domain_summary:
        domain_summary[domain] = {"count": 0, "severity_sum": 0}

    domain_summary[domain]["count"] += 1
    domain_summary[domain]["severity_sum"] += r.get("severity", 0)

# KPI CARDS
cols = st.columns(len(domain_summary))

for i, (domain, data) in enumerate(domain_summary.items()):
    avg_sev = round(data["severity_sum"] / data["count"], 2) if data["count"] > 0 else 0

    cols[i].metric(
        label=f"{domain}",
        value=f"{data['count']} issues",
        delta=f"Avg Severity: {avg_sev}"
    )

st.divider()

# ================= DOMAIN TABS =================
domains = list(domain_summary.keys())
tabs = st.tabs(domains)

for i, domain in enumerate(domains):
    with tabs[i]:

        st.subheader(f"{domain} Analysis")
        
        domain_match = "finance" if domain == "Financial" else domain.lower()
        domain_risks = [
            r for r in risks if r.get("domain", "").lower() == domain_match
        ]

        # --- DOMAIN INSIGHTS ---
        high_count = len([r for r in domain_risks if r.get("severity", 0) >= 8])
        avg_sev = round(sum([r.get("severity", 0) for r in domain_risks]) / len(domain_risks), 2) if len(domain_risks) > 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("High Risk Issues", high_count)
        col2.metric("Average Severity", avg_sev)

        st.write("---")

        if not domain_risks:
            st.success(f"No {domain} risks detected!")
        else:
            # --- RISKS LIST ---
            for idx, risk in enumerate(domain_risks):

                sev = risk.get('severity', 0)
                icon = "🔴" if sev >= 8 else "🟡" if sev >= 5 else "🟢"

                with st.container(border=True):

                    # TITLE
                    st.markdown(
                        f"**{icon} {risk.get('risk')}**"
                    )

                    # QUICK INFO
                    st.caption(
                        f"Severity: {sev} | Probability: {risk.get('probability', 'N/A')} | Confidence: {risk.get('confidence_score', 'N/A')}"
                    )

                    # --- RECOMMENDATION ---
                    rec = risk.get('recommendation', '')
                    if rec and str(rec).lower() != 'n/a':
                        st.markdown(f"**💡 Recommendation:** {rec}")

                    # --- EXPANDABLE EXPLANATION ---
                    with st.expander("🧠 Explain this analysis"):

                        st.markdown("**📝 Source Clause:**")
                        quote = risk.get('quote', '')
                        if quote and str(quote).lower() not in ['n/a', 'exact text from contract if available']:
                            st.info(f"*{quote}*")

                        st.markdown("**🧠 Reasoning Pathway:**")
                        steps = risk.get('reasoning_steps', [])
                        for step_idx, step in enumerate(steps):
                            st.caption(f"Step {step_idx+1}: {step}")

        # --- DOMAIN LEVEL INSIGHT ---
        st.divider()

        st.subheader("📌 Domain Insight")

        if avg_sev >= 7:
            st.error(f"🔴 {domain} domain shows high risk concentration.")
        elif avg_sev >= 5:
            st.warning(f"🟡 {domain} domain shows moderate risk levels.")
        else:
            st.success(f"🟢 {domain} domain is relatively safe.")