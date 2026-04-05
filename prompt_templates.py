# ==========================
# LEGAL PROMPT
# ==========================
LEGAL_PROMPT = """
Analyze legal risks.

Return:
- Top Legal Risks: only
1.
2.
3.
- Keep it simple
- Max 100 words
- Simple language

{text}
"""

# ==========================
# FINANCE PROMPT
# ==========================
FINANCE_PROMPT = """
Analyze financial risks.

Return:
- Top Financial Risks:
1.
2.
3.
- Keep it simple
- Bullet points
- Max 60 words

{text}
"""

# ==========================
# COMPLIANCE PROMPT
# ==========================
COMPLIANCE_PROMPT = """
Check compliance Risks.

Return:
- Top Compliance Risks
1.
2.
3.
- Keep it simple
- Bullet points
- Max 60 words

{text}
"""

# ==========================
# OPERATIONS PROMPT  ✅ NEW
# ==========================
OPERATIONS_PROMPT = """
Analyze operational risks.

Return:
- Top Operational Risks:
1.
2.
3.
- Keep it simple
- Bullet points
- Max 60 words

{text}
"""

# ==========================
# Operation 
# ==========================

OPERATIONS_PROMPT = """
You are an Operations Specialist Agent. Analyze the contract from an operational standpoint.
Focus on:
- delivery timelines
- SLA requirements
- operational risks
- resource dependencies
- process gaps
- feasibility issues

Return output in JSON:
{
    "operations_risk_score": <0-100>,
    "operations_findings": [],
    "operations_risk_level": ""
}
"""


# ==========================
# SUMMARY PROMPT
# ==========================
SUMMARY_PROMPT = """
Give a 4-line Executive Summary.

Do NOT explain changes.
Do NOT describe analysis.

Only summarize key:
- Legal risks
- Financial risks
- Compliance issues
- Operational risks

Keep it short and professional.

{text}
"""
