from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


def generate_pdf_report(report_text: str, file_name: str):

    pdf_file = f"{file_name}_report.pdf"

    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    title = ParagraphStyle(
        name="Title",
        fontSize=20,
        spaceAfter=20,
        alignment=1,
        textColor=colors.black
    )

    header = ParagraphStyle(
        name="Header",
        fontSize=14,
        spaceAfter=10,
        textColor=colors.black
    )

    body = ParagraphStyle(
        name="Body",
        fontSize=10,
        leading=14,
        spaceAfter=8
    )

    content = []

    # Title
    content.append(Paragraph("Contract Analysis Report", title))
    content.append(Spacer(1, 20))

    # Clean text
    clean = report_text.replace("#", "")
    clean = clean.replace("##", "")
    clean = clean.replace("---", "")

    sections = clean.split("\n\n")

    for sec in sections:
        if not sec.strip():
            continue

        if "Analysis" in sec or "Summary" in sec:
            content.append(Paragraph(f"<b>{sec}</b>", header))
        else:
            content.append(Paragraph(sec.replace("\n", "<br/>"), body))

        content.append(Spacer(1, 10))

    doc.build(content)

    return pdf_file