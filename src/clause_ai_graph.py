from typing import TypedDict, List, Optional, Annotated
import operator
import uuid
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from src.config import get_llm, get_embeddings, get_pinecone_index
from src.prompts import (
    LEGAL_SYSTEM_PROMPT, 
    FINANCE_SYSTEM_PROMPT, 
    COMPLIANCE_SYSTEM_PROMPT, 
    OPERATIONS_SYSTEM_PROMPT
)

# 1. Define the Multi-Agent State [cite: 20]
class AgentState(TypedDict):
    query: str
    contract_type: str
    review_plan: List[str]
    # Annotated with operator.ior allows agents to merge results into one dict [cite: 22]
    analysis_results: Annotated[dict, operator.ior] 
    final_report: Optional[str]
    tone: str
    structure: str
    focus: str

class ClauseAIGraph:
    def __init__(self):
        self.llm = get_llm()
        self.embeddings = get_embeddings()
        self.pinecone_index = get_pinecone_index()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Builds the multi-agent workflow architecture per System Design [cite: 19, 20]"""
        workflow = StateGraph(AgentState)

        # Define all nodes based on the methodology workflow [cite: 5, 15]
        workflow.add_node("classify_contract", self.classify_contract)
        workflow.add_node("create_review_plan", self.create_review_plan)
        workflow.add_node("legal_analysis", self.legal_analysis)
        workflow.add_node("finance_analysis", self.finance_analysis)
        workflow.add_node("compliance_analysis", self.compliance_analysis)
        workflow.add_node("operations_analysis", self.operations_analysis)
        workflow.add_node("generate_final_report", self.generate_final_report)

        # Build Flow [cite: 23, 30]
        workflow.set_entry_point("classify_contract")
        workflow.add_edge("classify_contract", "create_review_plan")
        
        # Milestone 3 Parallel Pipeline
        workflow.add_edge("create_review_plan", "legal_analysis")
        workflow.add_edge("create_review_plan", "finance_analysis")
        workflow.add_edge("create_review_plan", "compliance_analysis")
        workflow.add_edge("create_review_plan", "operations_analysis")

        workflow.add_edge("legal_analysis", "generate_final_report")
        workflow.add_edge("finance_analysis", "generate_final_report")
        workflow.add_edge("compliance_analysis", "generate_final_report")
        workflow.add_edge("operations_analysis", "generate_final_report")
        
        workflow.add_edge("generate_final_report", END)

        return workflow.compile()

    # --- Node Functions ---

    # Inside ClauseAIGraph class in clause_ai_graph.py
    def classify_contract(self, state: AgentState) -> AgentState:
        print("--- CLASSIFYING CONTRACT ---")
        try:
            # Tweak prompt for Grok's instruction following [cite: 38]
            prompt = ChatPromptTemplate.from_template(
                "System: You are a legal classifier. Analyze the query and return ONLY the "
                "category name (e.g., 'Employment Agreement', 'NDA', 'Service Agreement').\n"
                "Query: {query}"
            )
            chain = prompt | self.llm
            response = chain.invoke({"query": state["query"]})
            # Clean response in case Grok adds conversational filler
            category = response.content.strip().split('\n')[0]
            return {"contract_type": category}
        except Exception as e:
            print(f"⚠️ Error in Classification: {e}")
            return {"contract_type": "General Contract"}


    def create_review_plan(self, state: AgentState) -> AgentState:
        """Coordinator node manages task distribution based on focus [cite: 8, 21]"""
        print(f"--- CREATING PLAN FOR: {state['contract_type']} ---")
        focus = state.get("focus", "All Domains")
        if focus == "Legal & Compliance Only":
            return {"review_plan": ["legal", "compliance"]}
        elif focus == "Finance & Operations Only":
            return {"review_plan": ["finance", "operations"]}
        else:
            return {"review_plan": ["legal", "finance", "compliance", "operations"]}


    def _get_context(self, query_terms: str) -> str:
        texts = [] # Initialize empty list first
        try:
            query_embedding = self.embeddings.embed_query(query_terms)
            results = self.pinecone_index.query(
                vector=query_embedding, 
                top_k=5, 
                include_metadata=True,
                namespace="default"
            )
            texts = [match["metadata"]["text"] for match in results.get("matches", []) if "text" in match["metadata"]]
        except Exception as e:
            print(f"❌ Retrieval Error: {e}")
            return "" # Return empty string on error

        return "\n".join(texts) if texts else ""
    

    def _store_intermediate_result(self, domain: str, content: str, original_query: str):
        try:
            vector = self.embeddings.embed_query(content)
            record_id = f"intermediate_{domain}_{str(uuid.uuid4())[:8]}"
            self.pinecone_index.upsert(
                vectors=[{
                    "id": record_id,
                    "values": vector,
                    "metadata": {
                        "domain": domain,
                        "text": content,
                        "original_query": original_query,
                        "type": "intermediate_analysis"
                    }
                }],
                namespace="intermediate_results"
            )
            print(f"✅ Stored {domain} analysis in Pinecone.")
        except Exception as e:
            print(f"⚠️ Failed to store intermediate result for {domain}: {e}")

    def _run_agent_pipeline(self, domain: str, query_terms: str, system_prompt: str, state: AgentState) -> AgentState:
        # Check review plan for focus customization
        if domain not in state.get("review_plan", []):
            return {"analysis_results": {}}

        print(f"--- {domain.upper()} DOMAIN ANALYSIS ---")
        context = self._get_context(query_terms)
        
        # SAFETY GATE: If no context was found, do not call the LLM
        if not context or context.strip() == "":
            analysis_content = f"No relevant {domain} clauses found for analysis."
        else:
            prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("human", "{context}")])
            response = (prompt | self.llm).invoke({"context": context})
            analysis_content = response.content

        # Store intermediate result in pinecone
        self._store_intermediate_result(domain, analysis_content, state["query"])
        
        return {"analysis_results": {domain: analysis_content}}

    def legal_analysis(self, state: AgentState) -> AgentState:
        return self._run_agent_pipeline("legal", "indemnification liability governing law intellectual property", LEGAL_SYSTEM_PROMPT, state)

    def finance_analysis(self, state: AgentState) -> AgentState:
        return self._run_agent_pipeline("finance", "payment terms penalties fees financial obligations", FINANCE_SYSTEM_PROMPT, state)

    def compliance_analysis(self, state: AgentState) -> AgentState:
        """Compliance Agent: Analyzes Regulatory Risk [cite: 4, 34]"""
        return self._run_agent_pipeline("compliance", "GDPR privacy data protection regulatory compliance audit", COMPLIANCE_SYSTEM_PROMPT, state)

    def operations_analysis(self, state: AgentState) -> AgentState:
        """Operations Agent: Analyzes Execution & Timelines [cite: 4, 34]"""
        return self._run_agent_pipeline("operations", "SLA delivery milestones renewal dates performance", OPERATIONS_SYSTEM_PROMPT, state)


    def generate_final_report(self, state: AgentState) -> AgentState:
        """Synthesizes outputs into actionable reports customized by tone/structure [cite: 13, 14, 46]"""
        print("--- GENERATING FINAL REPORT ---")
        tone = state.get("tone", "Professional")
        structure = state.get("structure", "Detailed Analysis")
        
        findings = "\n\n".join([f"### {k.upper()} ANALYSIS\n{v}" for k, v in state["analysis_results"].items()])
        prompt = ChatPromptTemplate.from_template(
            "As a Senior Contract Analyst, synthesize these domain findings into a {tone} report "
            "using a {structure} structure. Highlight major risks and recommendations based on the findings:\n\n{findings}"
        )
        report = (prompt | self.llm).invoke({
            "tone": tone, 
            "structure": structure, 
            "findings": findings
        })
        return {"final_report": report.content}


    def run(self, query: str, tone: str = "Professional", structure: str = "Detailed Analysis", focus: str = "All Domains"):
        """Executes the analysis pipeline with customization options [cite: 21]"""
        initial_state = {
            "query": query, 
            "analysis_results": {}, 
            "review_plan": [],
            "tone": tone,
            "structure": structure,
            "focus": focus
        }
        return self.graph.invoke(initial_state)

if __name__ == "__main__":
    app = ClauseAIGraph()
    result = app.run("Perform a full multi-domain audit of this contract for risks and obligations.")
    print("\n" + "="*30 + "\nFINAL AUDIT REPORT\n" + "="*30)
    print(result["final_report"])