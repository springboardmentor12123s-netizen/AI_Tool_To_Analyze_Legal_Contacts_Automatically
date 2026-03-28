import streamlit as st

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="ClauseAI Report Viewer",
    layout="wide"
)

# =====================================================
# IMPORTS
# =====================================================
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from io import BytesIO

# =====================================================
# SIDEBAR NAVIGATION
# =====================================================
st.sidebar.title("📂 Navigation")

st.sidebar.page_link("app.py", label="🏠 Home")
st.sidebar.page_link("pages/contract_analysis.py", label="📄 Analyze Contract")
st.sidebar.page_link("pages/report_viewer.py", label="📊 View Report")

# =====================================================
# PDF GENERATOR
# =====================================================
def generate_pdf(result):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*inch,
        leftMargin=1*inch,
        topMargin=1*inch,
        bottomMargin=1*inch
    )

    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("ClauseAI Report", styles["Title"]))
    content.append(Spacer(1, 10))
    content.append(Paragraph("Multi-Domain Contract Analysis", styles["Heading2"]))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    content.append(Spacer(1, 20))

    sections = [
        ("Compliance", result.get("compliance_report")),
        ("Legal", result.get("legal_report")),
        ("Financial", result.get("finance_report")),
        ("Operations", result.get("operations_report")),
    ]

    for title, text in sections:
        content.append(Paragraph(title, styles["Heading3"]))
        content.append(Spacer(1, 8))

        formatted = text.replace("\n", "<br/>") if text else "No data available."
        content.append(Paragraph(formatted, styles["BodyText"]))
        content.append(Spacer(1, 15))

    doc.build(content)
    buffer.seek(0)
    return buffer

# =====================================================
# MAIN UI
# =====================================================
def show_report():

    st.markdown(
        "<h1 style='color:#1f4e79;'>📊 ClauseAI Report Dashboard</h1>",
        unsafe_allow_html=True
    )

    # -----------------------------
    # CHECK DATA
    # -----------------------------
    if "analysis_result" not in st.session_state:
        st.warning("No analysis found. Please analyze a contract first.")

        if st.button("📄 Go to Analysis"):
            st.switch_page("pages/contract_analysis.py")

        return

    result = st.session_state["analysis_result"]

    config = st.session_state.get("report_config", {
        "tone": "formal",
        "structure": "bullet",
        "focus": ["all"]
    })

    # =====================================================
    # EXECUTIVE SUMMARY (NEW)
    # =====================================================
    st.subheader("🧠 Executive Summary")

    summary = result.get("summary", None)

    if summary:
        st.info(summary)
    else:
        st.info("AI-generated summary not available. Showing extracted insights below.")

    # =====================================================
    # CONFIG DISPLAY (NEW)
    # =====================================================
    with st.expander("⚙ Report Configuration"):
        st.write("**Tone:**", config["tone"])
        st.write("**Structure:**", config["structure"])
        st.write("**Focus Areas:**", ", ".join(config["focus"]))

    st.divider()

    st.success("Analysis completed successfully!")

    # =====================================================
    # TABS
    # =====================================================
    tabs = st.tabs(["⚖ Compliance", "📜 Legal", "💰 Financial", "⚙ Operations"])

    sections = [
        "compliance_report",
        "legal_report",
        "finance_report",
        "operations_report"
    ]

    for i, tab in enumerate(tabs):
        with tab:
            st.markdown('<div style="padding:15px;background:#f8f9fc;border-radius:10px;">', unsafe_allow_html=True)

            text = result.get(sections[i])

            if text:
                st.write(text)
            else:
                st.warning("No data available")

            st.markdown('</div>', unsafe_allow_html=True)

    # =====================================================
    # FEEDBACK SYSTEM (NEW - IMPORTANT FOR INTERNSHIP)
    # =====================================================
    st.divider()
    st.subheader("⭐ Feedback")

    col1, col2 = st.columns(2)

    with col1:
        rating = st.slider("Rate this report", 1, 5, 4)

    with col2:
        comment = st.text_area("Comments")

    if st.button("Submit Feedback"):

        if "feedback_store" not in st.session_state:
            st.session_state["feedback_store"] = []

        st.session_state["feedback_store"].append({
            "rating": rating,
            "comment": comment
        })

        st.success("Thank you for your feedback!")

    # =====================================================
    # PDF EXPORT
    # =====================================================
    st.divider()

    if st.button("📄 Generate PDF Report"):

        with st.spinner("Generating PDF..."):
            pdf_buffer = generate_pdf(result)

            st.download_button(
                "⬇ Download PDF",
                pdf_buffer,
                file_name="ClauseAI_Report.pdf",
                mime="application/pdf"
            )

    # =====================================================
    # NAVIGATION
    # =====================================================
    st.divider()

    if st.button("🔄 Analyze Another Contract"):
        st.switch_page("pages/contract_analysis.py")


# RUN
show_report()