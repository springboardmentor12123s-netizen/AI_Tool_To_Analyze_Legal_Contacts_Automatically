import re
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

FINANCIAL_RISK_CATEGORIES = {
    "PAYMENT": ["net 30", "net 60", "overdue", "late payment", "invoice", "payment terms"],
    "PENALTY": ["liquidated damages", "penalty", "fine", "forfeit"],
    "LIABILITY": ["liability limited to", "maximum liability", "cap on damages", "liability cap"],
    "INDEMNITY": ["indemnify", "hold harmless", "defend against", "indemnification"],
    "CURRENCY": ["usd", "eur", "gbp", "exchange rate", "currency"]
}

class FinanceFinding(BaseModel):
    risk_category: str = Field(description="PAYMENT, PENALTY, LIABILITY, INDEMNITY, CURRENCY, or NONE", default="NONE")
    exposure_amount: str = Field(description="Numeric value or 'undefined'", default="undefined")
    risk_score: int = Field(description="Risk score from 1 (lowest) to 10 (highest)", default=0)
    red_flags: List[str] = Field(description="List of specific concerns found", default_factory=list)
    suggested_mitigation: str = Field(description="Suggested mitigation strategy", default="None")

class FinancialRiskPipeline:
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=FinanceFinding)
        
        template = """
        You are a financial risk analyst reviewing contract clauses.
        Identify financial exposure in the following clause.
        
        Category Context: {category_context}
        
        Clause: {clause}
        
        {format_instructions}
        """
        
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["category_context", "clause"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        self.chain = self.prompt | self.llm | self.parser
        
    def _classify_category(self, clause: str) -> str:
        """Fast keyword pre-filter to detect potential risk categories."""
        clause_lower = clause.lower()
        detected_categories = []
        for category, keywords in FINANCIAL_RISK_CATEGORIES.items():
            for kw in keywords:
                if kw in clause_lower:
                    detected_categories.append(category)
                    break # Move to next category if one keyword hits
        
        if not detected_categories:
            return "NONE"
        return ", ".join(detected_categories)

    def run(self, clauses: List[str]) -> List[Dict[str, Any]]:
        results = []
        for clause in clauses:
            try:
                # 1. Fast Pre-filter
                category_context = self._classify_category(clause)
                
                # If definitely no keywords, we might skip LLM to save cost, 
                # but for safety/accuracy we'll ask LLM anyway, passing the context.
                # In production, if category == "NONE", you might append a default safe dict and `continue`.
                
                # 2. LLM Deep Analysis
                result = self.chain.invoke({
                    "category_context": f"Potential categories detected: {category_context}",
                    "clause": clause
                })
                
                output = result.model_dump()
                # Ensure we capture the pre-filter context if LLM missed it
                if output["risk_category"] == "NONE" and category_context != "NONE":
                    output["risk_category"] = category_context
                    
                results.append(output)
            except Exception as e:
                print(f"[Finance Pipeline] Error processing clause: {e}")
                results.append({
                    "risk_category": "ERROR",
                    "exposure_amount": "UNKNOWN",
                    "risk_score": 0,
                    "red_flags": [f"Failed extraction: {str(e)}"],
                    "suggested_mitigation": ""
                })
        return results
