from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# Define the expected JSON output structure
class OperationsFinding(BaseModel):
    operational_requirement: str = Field(description="The operational task, SLA, or deliverable mentioned in the clause", default="None")
    feasibility_risk: str = Field(description="Risk level of failing to meet the operational requirement: HIGH, MEDIUM, LOW, or NONE", default="NONE")
    timeline_impact: str = Field(description="Impact on project timelines, schedules, or delivery dates", default="No timeline specified")
    resource_needs: str = Field(description="Required resources (personnel, software, hardware) to fulfill the obligation", default="None specified")

class OperationsPipeline:
    def __init__(self, llm: ChatGroq):
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=OperationsFinding)
        
        template = """
        You are an Operations Manager. Analyze the following contract clause.
        Identify risks and requirements related to: deliverables, Service Level Agreements (SLAs), operational timelines, and resource allocation.
        
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
        """Run the operations extraction on a list of clauses concurrently."""
        results = []
        for clause in clauses:
            try:
                # LLM execution
                result = self.chain.invoke({"clause": clause})
                results.append(result.model_dump())
            except Exception as e:
                print(f"[Operations Pipeline] Error processing clause: {e}")
                results.append({
                    "operational_requirement": "ERROR",
                    "feasibility_risk": "UNKNOWN",
                    "timeline_impact": f"Failed extraction: {str(e)}",
                    "resource_needs": ""
                })
        return results
