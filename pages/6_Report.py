import streamlit as st
import sys, os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css

st.set_page_config(page_title="Executive Report", layout="wide", page_icon="📑")
inject_custom_css()

st.title("📑 Consolidated Executive Report")
st.caption("Auto-generated comprehensive report based on multi-agent findings.")

# --- CHECK DATA ---
if "analysis_results" not in st.session_state or not st.session_state.analysis_results:
    st.warning("No contracts analyzed yet. Please go to the Upload page.")
    st.stop()

results = st.session_state.analysis_results

# --- GENERATE CONSOLIDATED REPORT TEXT ---
def generate_report(results, format="Markdown"):
    
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_parts = []
    
    if format == "Markdown":
        report_parts.append(f"# Executive Contract Portfolio Analysis\n**Generated On:** {date_str}\n---\n")
    else:
        report_parts.append(f"EXECUTIVE CONTRACT PORTFOLIO ANALYSIS\nGenerated On: {date_str}\n========================================\n\n")

    for res in results:
        file_name = res.get("file", "Unknown")
        final_report = res.get("final_report", "No report available.")

        # Extract KPIs
        risks = res.get("metrics", {}).get("risks", []) if res.get("metrics") else []
        total = len(risks)
        high = len([r for r in risks if r.get("severity", 0) >= 8])

        if format == "Markdown":
            report_parts.append(f"## Document: {file_name}\n")
            report_parts.append(f"**Total Issues:** {total} | **High Severity:** {high}\n")
            report_parts.append(final_report)
            report_parts.append("\n---\n")
        else:
            report_parts.append(f"DOCUMENT: {file_name}\n")
            report_parts.append(f"Total Issues: {total} | High Severity: {high}\n")
            report_parts.append(final_report)
            report_parts.append("\n----------------------------------------\n\n")

    return "\n".join(report_parts)

# --- UI OPTIONS ---
col1, col2 = st.columns(2)

with col1:
    report_format = st.radio("Download Format", ["Markdown", "Plain Text"])
with col2:
    include_highlights = st.checkbox("Include visual highlight markings in export", value=False)

# Render Preview
st.subheader("👁️ Preview")

report_text = generate_report(results, report_format)

if not include_highlights:
    # Strip HTML highlights if present in raw prompt outputs
    report_text = report_text.replace('<mark>', '').replace('</mark>', '')

with st.container(border=True):
    if report_format == "Markdown":
        st.markdown(report_text, unsafe_allow_html=True)
    else:
        st.text(report_text)

# --- DOWNLOAD BUTTON ---
st.divider()

if report_format == "Markdown":
    data = report_text.encode('utf-8')
    mime = "text/markdown"
    ext = "md"
else:
    data = report_text.encode('utf-8')
    mime = "text/plain"
    ext = "txt"

st.download_button(
    label="⬇️ Download Complete Report",
    data=data,
    file_name=f"Executive_Contract_Report.{ext}",
    mime=mime,
    use_container_width=True,
    type="primary"
)