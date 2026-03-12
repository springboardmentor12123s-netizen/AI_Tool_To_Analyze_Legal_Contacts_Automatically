from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Define the expected JSON output structure
class LegalFinding(BaseModel):
    clause_type: str = Field(description="The legal nature of the clause, e.g., Warranty, Indemnification, Jurisdiction, Termination, or General", default="General")
    legal_risk: str = Field(description="Risk level from a legal perspective: HIGH, MEDIUM, LOW, or NONE", default="NONE")
    liability_description: str = Field(description="Description of potential legal liability, governing law issues, or unbalanced terms", default="No significant liability detected")
    recommendation: str = Field(description="Suggested action for legal counsel (e.g., 'Rewrite cap', 'Negotiate venue')", default="None")

class LegalPipeline:
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=LegalFinding)
        
        template = """
        You are a Legal Counsel expert. Analyze the following contract clause.
        Identify legal risks related to: warranties, liabilities, indemnification, jurisdiction, or termination rights.
        
        Clause: {clause}
        
        {format_instructions}
        """
        
        self.prompt = PromptTemplate(
            template=template,
            input_variables=["clause"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        self.chain = self.prompt | self.llm | self.parser
        
    def run(self, clauses: List[str]) -> List[Dict[str, Any]]:
        """Run the legal extraction on a list of clauses concurrently."""
        results = []
        for clause in clauses:
            try:
                # LLM execution
                result = self.chain.invoke({"clause": clause})
                results.append(result.model_dump())
            except Exception as e:
                print(f"[Legal Pipeline] Error processing clause: {e}")
                results.append({
                    "clause_type": "ERROR",
                    "legal_risk": "UNKNOWN",
                    "liability_description": f"Failed extraction: {str(e)}",
                    "recommendation": ""
                })
        return results
