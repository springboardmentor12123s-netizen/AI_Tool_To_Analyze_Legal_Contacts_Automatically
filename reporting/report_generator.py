from utils.groq_llm import groq_chat
from datetime import datetime


# ----------------------------------------
# 🔹 Helper: Combine Report
# ----------------------------------------

def _combine_report(report: dict) -> str:
    return f"""
Legal:
{report['legal_r2']}

Finance:
{report['finance_r2']}

Compliance:
{report['compliance_r2']}

Operations:
{report['operations_r2']}
"""


# ----------------------------------------
# 1. Executive Summary
# ----------------------------------------

def generate_executive_summary(report: dict) -> str:
    combined = _combine_report(report)

    prompt = f"""
You are a senior contract analyst.

Summarize ONLY key risks.

STRICT:
- Max 4 bullets
- Each bullet = issue + impact
- No generic lines
- No repetition
- No new info

{combined}

Return:
- ...
"""

    return groq_chat(prompt, combined)


# ----------------------------------------
# 2. Cross-Domain Insights
# ----------------------------------------

def generate_cross_insights(report: dict) -> str:
    combined = _combine_report(report)

    prompt = f"""
Find cross-domain risks.

STRICT:
- Max 3 bullets
- Show cause → impact
- No generic lines

{combined}

Return:
- ...
"""

    return groq_chat(prompt, combined)


# ----------------------------------------
# 3. Final Report (MARKDOWN FORMAT)
# ----------------------------------------

def generate_final_report(
    report: dict,
    tone="professional",
    focus="balanced",
    contract_name="Contract"
):

    summary = generate_executive_summary(report)
    cross = generate_cross_insights(report)

    date = datetime.now().strftime("%d %B %Y")

    final_report = f"""
# 📄 Contract Analysis Report

**Contract:** {contract_name}  
**Date:** {date}  
**Focus:** {focus}  
**Tone:** {tone}  

---

## 🔍 Executive Summary
{summary}

---

## ⚖️ Legal Analysis
{report['legal_r2']}

---

## 💰 Financial Analysis
{report['finance_r2']}

---

## 🛡 Compliance Analysis
{report['compliance_r2']}

---

## ⚙️ Operational Analysis
{report['operations_r2']}

---

## 🔗 Cross-Domain Insights
{cross}

---

## ✅ Key Recommendations
- Address high-risk clauses before approval  
- Align compliance obligations with operations  
- Validate penalty and payment structures  

---
"""

    return final_report.strip()