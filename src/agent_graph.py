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

COMPLIANCE_PROMPT = """You are a Compliance Analyst AI. 
Review the following contract text for regulatory compliance issues, adherence to standards, and potential violations.
Focus on: GDPR, data privacy, industry specific regulations.
Contract Text:
{contract_text}
"""

FINANCE_PROMPT = """You are a Finance Analyst AI.
Review the following contract text for financial risks, payment terms, penalties, and fiscal obligations.
Focus on: Payment schedules, currency, late fees, tax implications.
Contract Text:
{contract_text}
"""

LEGAL_PROMPT = """You are a Legal Analyst AI.
Review the following contract text for legal risks, liability clauses, indemnification, and dispute resolution logic.
Focus on: Liability caps, jurisdiction, arbitration, termination rights.
Contract Text:
{contract_text}
"""

OPERATIONS_PROMPT = """You are an Operations Analyst AI.
Review the following contract text for operational feasibility, service level agreements (SLAs), and delivery timelines.
Focus on: Deliverables, timelines, dependencies, resource requirements.
Contract Text:
{contract_text}
"""

# --- Node Functions ---

def compliance_agent(state: AgentState):
    print("--- Compliance Agent Working ---")
    response = llm.invoke(COMPLIANCE_PROMPT.format(contract_text=state["contract_text"]))
    return {"compliance_analysis": response.content}

def finance_agent(state: AgentState):
    print("--- Finance Agent Working ---")
    response = llm.invoke(FINANCE_PROMPT.format(contract_text=state["contract_text"]))
    return {"finance_analysis": response.content}

def legal_agent(state: AgentState):
    print("--- Legal Agent Working ---")
    response = llm.invoke(LEGAL_PROMPT.format(contract_text=state["contract_text"]))
    return {"legal_analysis": response.content}

def operations_agent(state: AgentState):
    print("--- Operations Agent Working ---")
    response = llm.invoke(OPERATIONS_PROMPT.format(contract_text=state["contract_text"]))
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
