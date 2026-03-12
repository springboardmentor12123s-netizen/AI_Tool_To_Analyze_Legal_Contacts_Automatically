import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from src.pipelines.compliance import CompliancePipeline
from src.pipelines.finance import FinancialRiskPipeline
from src.pipelines.legal import LegalPipeline
from src.pipelines.operations import OperationsPipeline
from langchain_groq import ChatGroq

# Note: In a real system, you'd inject the LLM or handle connections globally.
DOMAINS = ["compliance", "financial_risk", "legal", "operations"]

class ParallelExtractor:
    def __init__(self, llm: ChatGroq):
        self.pipelines = {
            "compliance": CompliancePipeline(llm=llm),
            "financial_risk": FinancialRiskPipeline(llm=llm),
            "legal": LegalPipeline(llm=llm),
            "operations": OperationsPipeline(llm=llm)
        }
        
    def _run_pipeline_sync(self, domain: str, clauses: List[str]) -> List[Dict[str, Any]]:
        """Synchronous wrapper for thread pool."""
        pipeline = self.pipelines.get(domain)
        if not pipeline:
            return [{"error": f"No pipeline for domain '{domain}'"}]
        return pipeline.run(clauses)

    async def extract_domain_clauses(self, clauses: List[str], domain: str) -> Dict[str, Any]:
        """Runs a specific domain pipeline in a separate thread."""
        loop = asyncio.get_event_loop()
        # Since LangChain's standard chains we wrote are sync, we wrap them in a ThreadPool
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, self._run_pipeline_sync, domain, clauses)
        return {"domain": domain, "results": result}

    async def parallel_extract_all(self, clauses: List[str]) -> Dict[str, Any]:
        """Runs all configured domain pipelines on the clauses concurrently."""
        tasks = [self.extract_domain_clauses(clauses, domain) for domain in self.pipelines.keys()]
        
        # All domains run simultaneously
        results = await asyncio.gather(*tasks)
        
        # Format the output mapping domain -> results
        final_output = {}
        for res in results:
            final_output[res["domain"]] = res["results"]
            
        return final_output
