from pydantic import BaseModel
from typing import List, Dict, Any

class ReportConfig(BaseModel):
    tone: str = "formal" # "formal", "concise", "executive"
    structure: List[str] = ["summary", "risks", "clauses"]
    focus: List[str] = [] # e.g. ["liability", "payment_terms", "termination"]

class ReportGenerator:
    def __init__(self, config: ReportConfig):
        self.tone = config.tone
        self.structure = config.structure
        self.focus = config.focus

    def _render_section(self, section_name: str, analysis: Dict[str, Any], raw_risks: Dict[str, str]) -> str:
        # We can implement specific rendering logic per section, driven by the LLM later or rule-based here.
        # For simplicity, we structure the output using the pre-generated text blocks.
        if section_name == "summary":
            return f"""## Executive Summary
This document was analyzed with a **{self.tone}** tone, focusing on **{', '.join(self.focus) if self.focus else 'general risks'}**.

**Compliance Overview**: {raw_risks.get('c_text', 'No compliance data.')}
**Financial Overview**: {raw_risks.get('f_text', 'No financial data.')}

"""
        elif section_name == "risks":
            return f"""## Document Risks
**Legal Risks**: {raw_risks.get('l_text', 'No legal risks.')}
**Operational Risks**: {raw_risks.get('o_text', 'No operational risks.')}
"""
        elif section_name == "clauses":
            return "## Extracted Clauses\nPlease see the structured JSON output for raw clause extractions."
            
        elif section_name == "recommendations":
            return """## Recommendations
1. Review all High-Risk exposures.
2. Ensure compliance checks pass before signing.
"""
        return ""

    def generate(self, contract_text: str, raw_risks: Dict[str, str]) -> str:
        focus_str = f"Ensure special attention is given to: {', '.join(self.focus)}." if self.focus else ""
        
        prompt_content = f"""
        You are a contract analyst. Analyze the following contract and extract:
        - Specific article numbers and their key obligations
        - Named parties, contract value ($USD), dates
        - Concrete risks with the exact clause reference (e.g. "Article 13 caps liability at X")
        - Specific recommendations tied to clauses
        
        Format your response in a {self.tone} tone. {focus_str}
        Make sure to include ONLY the following sections in your output, structured as Markdown:
        {', '.join(self.structure)}.
        
        Here are the focused risks identified by parallel domain agents:
        1. Compliance: {{c_text}}
        2. Financial: {{f_text}}
        3. Legal: {{l_text}}
        4. Operations: {{o_text}}
        
        Contract text:
        {{contract_text}}
        """
        
        return prompt_content
