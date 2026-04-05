from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# 🔥 LLM FOR TONE REWRITING
from llm_setup import groq_llm


# ==========================
# FONT SETUP (Times New Roman)
# ==========================
pdfmetrics.registerFont(TTFont('Times', 'times.ttf'))
pdfmetrics.registerFont(TTFont('Times-Bold', 'timesbd.ttf'))

PROJECT_NAME = "ClauseAI – Contract Risk Analysis"
AUTHOR_NAME = "Vaishnavi A. Kanade"


# ==========================
# REWRITE TEXT ACCORDING TO TONE
# ==========================
def rewrite_tone(text, tone):

    if tone is None or tone.strip() == "":
        return text

    tone = tone.lower().strip()

    # Safety fallback
    allowed = ["neutral", "professional", "friendly", "strict", "soft"]
    if tone not in allowed:
        return text

    prompt = f"""
Rewrite the following contract analysis text in a **{tone} tone**.
Keep meaning same. Do NOT add new points.

Text:
{text}
"""

    try:
        response = groq_llm.invoke(prompt)
        rewritten = response.content.strip()
        return rewritten
    except:
        return text



# ==========================
# HEADER + FOOTER
# ==========================
def header_footer(canvas, doc):
    width, height = A4

    canvas.setFont("Times", 10)

    # HEADER LEFT
    canvas.drawString(40, height - 30, PROJECT_NAME)

    # Header line
    canvas.line(40, height - 35, width - 40, height - 35)

    # FOOTER
    contract_name = getattr(doc, "contract_name", "Contract")

    canvas.line(40, 30, width - 40, 30)

    # LEFT BOTTOM → File name
    canvas.drawString(40, 15, contract_name)

    # RIGHT BOTTOM → Page number
    canvas.drawRightString(width - 40, 15, f"Page {doc.page}")


# ==========================
# FORMATTER
# ==========================
def format_text(text):

    if text is None:
        return "No content available."

    lines = str(text).split("\n")
    formatted = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("+") or line.startswith("-"):
            line = f"• {line[1:].strip()}"

        elif line.startswith("#"):
            line = f"<b>{line.replace('#','').strip()}</b>"

        elif ":" in line and len(line) < 60:
            line = f"<b>{line}</b>"

        elif line[:2].isdigit():
            line = f"{line}"

        formatted.append(line)

    return "<br/>".join(formatted) if formatted else "No structured content available."


# ==========================
# TABLE DETECTOR
# ==========================
def detect_table(text):

    if text is None:
        return None

    lines = str(text).split("\n")
    table_lines = [l for l in lines if "|" in l]

    if len(table_lines) < 2:
        return None

    table_data = []
    for row in table_lines:
        cols = [c.strip() for c in row.split("|") if c.strip()]
        if cols:
            table_data.append(cols)

    return table_data


# ==========================
# MAIN PDF GENERATOR
# ==========================
def generate_pdf(report_data, filename="report.pdf", tone="professional"):

    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=50
    )

    # Contract name
    contract_name = report_data.get("Contract Name") or "Contract Report"
    doc.contract_name = str(contract_name)
    doc.title = str(contract_name)

    styles = getSampleStyleSheet()

    # Styles
    title_style = ParagraphStyle(
        'Title',
        fontName='Times-Bold',
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=15
    )

    heading_style = ParagraphStyle(
        'Heading',
        fontName='Times-Bold',
        fontSize=14,
        spaceAfter=10
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Times',
        fontSize=12,
        alignment=TA_JUSTIFY,
        leading=16
    )

    right_align_style = ParagraphStyle(
        'RightAlign',
        fontName='Times',
        fontSize=12,
        alignment=TA_RIGHT
    )

    content = []

    # ==========================
    # TITLE
    # ==========================
    content.append(Paragraph(doc.title, title_style))
    content.append(Spacer(1, 15))

    # ==========================
    # SUMMARY TABLE
    # ==========================
    table_data = [
        ["Risk Score", str(report_data.get("Risk Score", "N/A"))],
        ["Confidence", str(report_data.get("Confidence", "N/A")) + "%"],
        ["Domains", report_data.get("Domains", "Legal, Finance, Compliance")],
        ["Status", report_data.get("Status", "Completed")]
    ]

    table = Table(table_data, colWidths=[150, 250])

    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTNAME", (0, 0), (-1, -1), "Times"),
        ("FONTSIZE", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    content.append(table)
    content.append(Spacer(1, 20))

    # ==========================
    # MAIN SECTIONS
    # ==========================
    for key, value in report_data.items():

        if key in ["Risk Score", "Confidence", "Domains", "Status"]:
            continue

        # SECTION TITLE
        content.append(Paragraph(str(key), heading_style))
        content.append(Spacer(1, 5))

        # Tone rewriting BEFORE formatting
        rewritten_value = rewrite_tone(value, tone)

        table_data = detect_table(rewritten_value)

        if table_data:
            table = Table(table_data)
            table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Times"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
            ]))
            content.append(table)

        else:
            clean_text = format_text(rewritten_value)
            content.append(Paragraph(clean_text, body_style))

        content.append(Spacer(1, 15))

    # AUTHOR SIGN
    content.append(Spacer(1, 40))
    content.append(Paragraph(AUTHOR_NAME, right_align_style))

    # BUILD PDF
    doc.build(
        content,
        onFirstPage=header_footer,
        onLaterPages=header_footer
    )

    return filename
