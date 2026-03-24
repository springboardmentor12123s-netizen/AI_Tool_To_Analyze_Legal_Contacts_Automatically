import os
import asyncio
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END, START

from src.parallel_extractor import ParallelExtractor
from src.pinecone_store import vector_store_manager

load_dotenv()

# --- State Definition ---
class AgentState(TypedDict, total=False):
    contract_text: str
    clauses: List[str]
    extracted_data: Dict[str, Any]
    final_report: str
    filename: str
    report_config: Dict[str, Any]

# --- LLM Initialization ---
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY")
)

# --- Node Functions ---

from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_contract_node(state: AgentState):
    """Splits the raw text into manageable clauses/paragraphs."""
    print("--- Orchestrator: Chunking Contract ---")
    text = state.get("contract_text", "")
    
    # Properly split large documents instead of hard-chopping at 20 paragraphs
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    clauses = text_splitter.split_text(text)
    
    print(f"  [Chunking] Generated {len(clauses)} candidate clauses.")
    return {"clauses": clauses}

async def extraction_node(state: AgentState):
    """Runs parallel pipelines and stores results in Pinecone."""
    print("--- Orchestrator: Running Parallel Extraction ---")
    clauses = state.get("clauses", [])
    
    if not clauses:
        return {"extracted_data": {}}

    extractor = ParallelExtractor(llm)
    # This runs Compliance and Finance pipelines concurrently
    results = await extractor.parallel_extract_all(clauses)
    
    # Store intermediate results in Pinecone
    print("--- Orchestrator: Storing Intermediate Results in Pinecone ---")
    
    for domain, findings_list in results.items():
        # findings_list is a list of Dicts (the JSON output of the pipeline)
        # It aligns 1:1 with the clauses list
        for idx, finding in enumerate(findings_list):
            
            # Very basic error/null filtering so we don't store garbage
            if isinstance(finding, dict):
                has_risk = finding.get("risk_level", "NONE") != "NONE" or finding.get("risk_category", "NONE") != "NONE"
                if has_risk or "ERROR" in str(finding):
                    metadata = {
                        "domain": domain,
                        "contract_id": state.get("filename", "unknown"),
                        **finding
                    }
                    vector_store_manager.store_clause(
                        clause_text=clauses[idx],
                        metadata=metadata
                    )

    return {"extracted_data": results}

def synthesis_node(state: AgentState):
    """Generates the final multi-domain risk report."""
    print("--- Orchestrator: Synthesizing Final Report ---")
    extracted_data = state.get("extracted_data", {})
    
    # We could query Pinecone here, or just use the extracted_data directly.
    # To prove Pinecone works, let's fetch the top risks from Pinecone!
    
    print("  [Synthesis] Retrieving top compliance risks from Pinecone...")
    compliance_risks = vector_store_manager.retrieve_similar(
        query="high risk regulatory violation GDPR HIPAA penalty",
        domain_filter="compliance",
        contract_id=state.get("filename"),
        top_k=3
    )
    
    print("  [Synthesis] Retrieving top financial risks from Pinecone...")
    finance_risks = vector_store_manager.retrieve_similar(
        query="high risk exposure penalty liability cap indemnification",
        domain_filter="financial_risk",
        contract_id=state.get("filename"),
        top_k=3
    )
    
    print("  [Synthesis] Retrieving top legal risks from Pinecone...")
    legal_risks = vector_store_manager.retrieve_similar(
        query="legal liability warranty jurisdiction termination breach of contract",
        domain_filter="legal",
        contract_id=state.get("filename"),
        top_k=3
    )
    
    print("  [Synthesis] Retrieving top operational requirements from Pinecone...")
    ops_risks = vector_store_manager.retrieve_similar(
        query="operational deliverables SLA timeline resource allocation failure",
        domain_filter="operations",
        contract_id=state.get("filename"),
        top_k=3
    )
    
    # Format prompts
    c_text = "\n".join([f"- {r['metadata']['text']} (Risk: {r['metadata'].get('risk_level', 'Unknown')})" for r in compliance_risks]) or "No major compliance risks detected."
    f_text = "\n".join([f"- {r['metadata']['text']} (Exposure: {r['metadata'].get('exposure_amount', 'Unknown')})" for r in finance_risks]) or "No major financial risks detected."
    l_text = "\n".join([f"- {r['metadata']['text']} (Risk: {r['metadata'].get('legal_risk', 'Unknown')})" for r in legal_risks]) or "No major legal risks detected."
    o_text = "\n".join([f"- {r['metadata']['text']} (Risk: {r['metadata'].get('feasibility_risk', 'Unknown')})" for r in ops_risks]) or "No major operational issues detected."
    
    # Handle Report Config
    raw_risks = {
        "c_text": c_text,
        "f_text": f_text,
        "l_text": l_text,
        "o_text": o_text
    }
    
    from src.report_generator import ReportConfig, ReportGenerator
    
    config_dict = state.get("report_config", {})
    report_config = ReportConfig(**config_dict)
    generator = ReportGenerator(report_config)
    
    # Generate the dynamic prompt based on config
    prompt_str = generator.generate(state.get("contract_text", ""), raw_risks)
    
    synthesis_prompt = PromptTemplate.from_template(prompt_str)
    
    response = llm.invoke(synthesis_prompt.format(
        contract_text=state.get("contract_text", "")[:30000],  # safety cap for massive docs
        c_text=c_text, 
        f_text=f_text,
        l_text=l_text,
        o_text=o_text
    ))
    return {"final_report": response.content}

# --- Graph Definition ---

workflow = StateGraph(AgentState)

workflow.add_node("chunking", chunk_contract_node)
workflow.add_node("extraction", extraction_node)
workflow.add_node("synthesis", synthesis_node)

workflow.add_edge(START, "chunking")
workflow.add_edge("chunking", "extraction")
workflow.add_edge("extraction", "synthesis")
workflow.add_edge("synthesis", END)

app = workflow.compile()
