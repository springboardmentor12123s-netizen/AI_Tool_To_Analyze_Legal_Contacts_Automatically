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

SUMMARY_PROMPT = """
Give a 4-line Executive Summary.

Do NOT explain changes.
Do NOT describe analysis.

Only summarize key:
- Legal risks
- Financial risks
- Compliance issues

Keep it short and professional.

{text}
"""


