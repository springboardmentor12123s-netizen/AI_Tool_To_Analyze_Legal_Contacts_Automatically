import os
from typing import TypedDict, List, Annotated
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import operator

load_dotenv()

# Define the State
class AgentState(TypedDict):
    contract_text: str
    compliance_analysis: str
    finance_analysis: str
    legal_analysis: str
    operations_analysis: str

# Initialize LLM
# Using Groq as per previous context, fallback to OpenAI if needed or configured
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile",
    api_key=os.environ.get("GROQ_API_KEY")
)

# --- Agent Prompts ---

# --- Agent Prompts ---

COMPLIANCE_PROMPT = """You are a Compliance Analyst AI. 
Review the following contract clauses for regulatory compliance issues, adherence to standards, and potential violations.
Focus on: GDPR, data privacy, industry specific regulations.
Context Clauses:
{context}
"""

FINANCE_PROMPT = """You are a Finance Analyst AI.
Review the following contract clauses for financial risks, payment terms, penalties, and fiscal obligations.
Focus on: Payment schedules, currency, late fees, tax implications.
Context Clauses:
{context}
"""

LEGAL_PROMPT = """You are a Legal Analyst AI.
Review the following contract clauses for legal risks, liability clauses, indemnification, and dispute resolution logic.
Focus on: Liability caps, jurisdiction, arbitration, termination rights.
Context Clauses:
{context}
"""

OPERATIONS_PROMPT = """You are an Operations Analyst AI.
Review the following contract clauses for operational feasibility, service level agreements (SLAs), and delivery timelines.
Focus on: Deliverables, timelines, dependencies, resource requirements.
Context Clauses:
{context}
"""

# --- Vector Store Helper ---
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
import time

# Initialize Pinecone Client
pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
index_name = os.environ.get("PINECONE_INDEX_NAME", "clauseai")

# Ensure index exists
if index_name not in pc.list_indexes().names():
    print(f"Creating Pinecone index: {index_name}")
    pc.create_index(
        name=index_name,
        dimension=384, # all-MiniLM-L6-v2 dimension
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )
    # Wait for index to be ready
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)

# Initialize Embeddings & Vector Store
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = PineconeVectorStore(index_name=index_name, embedding=embeddings)

def retrieve_context(query: str, k: int = 3) -> str:
    """Retrieve relevant clauses from Pinecone."""
    print(f"  [Retrieval] Querying: '{query}'")
    docs = vector_store.similarity_search(query, k=k)
    return "\n\n".join([d.page_content for d in docs])

# --- Node Functions ---

def compliance_agent(state: AgentState):
    print("--- Compliance Agent Working ---")
    # Retrieve relevant chunks
    context = retrieve_context("compliance regulation GDPR data privacy standard violation")
    # Invoke LLM
    response = llm.invoke(COMPLIANCE_PROMPT.format(context=context))
    return {"compliance_analysis": response.content}

def finance_agent(state: AgentState):
    print("--- Finance Agent Working ---")
    context = retrieve_context("payment fees penalty tax currency fiscal obligation")
    response = llm.invoke(FINANCE_PROMPT.format(context=context))
    return {"finance_analysis": response.content}

def legal_agent(state: AgentState):
    print("--- Legal Agent Working ---")
    context = retrieve_context("liability indemnification jurisdiction arbitration termination dispute")
    response = llm.invoke(LEGAL_PROMPT.format(context=context))
    return {"legal_analysis": response.content}

def operations_agent(state: AgentState):
    print("--- Operations Agent Working ---")
    context = retrieve_context("deliverables timeline SLA service level dependency resource")
    response = llm.invoke(OPERATIONS_PROMPT.format(context=context))
    return {"operations_analysis": response.content}

# --- Graph Definition ---

# --- Graph Definition ---

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("compliance", compliance_agent)
workflow.add_node("finance", finance_agent)
workflow.add_node("legal", legal_agent)
workflow.add_node("operations", operations_agent)

# Define edges - Parallel execution
# We can use the special START node to branch to multiple nodes at the beginning
from langgraph.graph import START

workflow.add_edge(START, "compliance")
workflow.add_edge(START, "finance")
workflow.add_edge(START, "legal")
workflow.add_edge(START, "operations")

workflow.add_edge("compliance", END)
workflow.add_edge("finance", END)
workflow.add_edge("legal", END)
workflow.add_edge("operations", END)

# Compile
app = workflow.compile()
