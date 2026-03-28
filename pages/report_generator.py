class ReportGenerator:
    """
    Converts multi-agent contract analysis into a structured final report
    with customization (tone, structure, focus).
    """

    def __init__(self, llm_client):
        self.llm = llm_client

    def build_report(self, analysis_result, config):
        """
        Generate final customized report from analysis output.
        """

        # -----------------------------
        # Extract config
        # -----------------------------
        tone = config.get("tone", "formal")
        structure = config.get("structure", "bullet")
        focus = config.get("focus", ["compliance", "legal", "finance", "operations"])

        # -----------------------------
        # Prepare structured input
        # -----------------------------
        analysis_text = f"""
COMPLIANCE REPORT:
{analysis_result.get("compliance_report", "")}

LEGAL REPORT:
{analysis_result.get("legal_report", "")}

FINANCIAL REPORT:
{analysis_result.get("finance_report", "")}

OPERATIONS REPORT:
{analysis_result.get("operations_report", "")}
"""

        # -----------------------------
        # Prompt for final report
        # -----------------------------
        prompt = f"""
You are an expert contract report generator.

Your task is to convert raw multi-domain analysis into a FINAL PROFESSIONAL REPORT.

---

RULES:
- Tone: {tone}
- Structure: {structure}
- Focus Areas: {", ".join(focus)}
- Do NOT add new facts
- Only reorganize and summarize given data
- Highlight risks clearly
- Provide actionable recommendations

---

OUTPUT FORMAT:

1. Executive Summary
2. Key Findings (by domain)
3. Risk Analysis
4. Recommendations
5. Final Conclusion

---

INPUT ANALYSIS:
{analysis_text}
"""

        # -----------------------------
        # LLM Call
        # -----------------------------
        response = self.llm(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional contract report generator assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=1200
        )

        return response.choices[0].message.content