from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


def generate_pdf(report_data, filename="report.pdf"):

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title = styles["Title"]
    heading = styles["Heading2"]
    body = styles["BodyText"]

    content = []

    # PDF Title
    content.append(Paragraph("Contract Analysis Report", title))
    content.append(Spacer(1, 20))

    for key, value in report_data.items():

        content.append(Paragraph(f"<b>{key}</b>", heading))
        content.append(Spacer(1, 10))
        content.append(Paragraph(str(value), body))
        content.append(Spacer(1, 20))

        # Add new page after summary
        if key == "Summary":
            content.append(PageBreak())

    doc.build(content)

    return filename