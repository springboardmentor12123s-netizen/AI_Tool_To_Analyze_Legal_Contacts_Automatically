from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Define the expected JSON output structure
class ComplianceFinding(BaseModel):
    regulation_type: str = Field(description="The regulation involved, e.g., GDPR, HIPAA, SOX, CCPA, or None", default="None")
    risk_level: str = Field(description="Risk level: HIGH, MEDIUM, LOW, or NONE", default="NONE")
    violation_description: str = Field(description="Description of the potential violation or compliance risk", default="No violation detected")
    recommendation: str = Field(description="Suggested action or recommendation to mitigate the risk", default="None")

class CompliancePipeline:
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=ComplianceFinding)
        
        template = """
        You are a compliance expert. Analyze the following contract clause.
        Identify violations or risks related to: GDPR, HIPAA, SOX, CCPA, or general data privacy regulations.
        
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
        """Run the compliance extraction on a list of clauses concurrently. 
        For now, this is a simple loop, but it acts on individual clauses."""
        results = []
        for clause in clauses:
            try:
                # LLM execution
                result = self.chain.invoke({"clause": clause})
                results.append(result.model_dump())
            except Exception as e:
                print(f"[Compliance Pipeline] Error processing clause: {e}")
                results.append({
                    "regulation_type": "ERROR",
                    "risk_level": "UNKNOWN",
                    "violation_description": f"Failed extraction: {str(e)}",
                    "recommendation": ""
                })
        return results
