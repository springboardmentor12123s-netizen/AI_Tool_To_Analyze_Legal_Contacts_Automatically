from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0
)


# ---------------- COMPLIANCE AGENT ----------------

def compliance_agent(state):

    contract = state["contract"]

    prompt = f"""
You are a compliance risk analyzer.

Identify the TOP 3 compliance risks in the contract.

STRICT RULES:
- Do NOT explain in paragraphs
- Return ONLY the structured format
- Keep answers short

FORMAT:

COMPLIANCE RISK 1
Clause:
Risk Type:
Risk Level:
Recommendation:

COMPLIANCE RISK 2
Clause:
Risk Type:
Risk Level:
Recommendation:

COMPLIANCE RISK 3
Clause:
Risk Type:
Risk Level:
Recommendation:

Contract:
{contract}
"""

    response = llm.invoke(prompt)

    return {"compliance_result": response.content}


# ---------------- LEGAL AGENT ----------------

def legal_agent(state):

    contract = state["contract"]
    compliance = state["compliance_result"]

    prompt = f"""
You are a legal contract analyst.

Use the compliance findings and identify the TOP 3 legal issues.

STRICT RULES:
- Do NOT write paragraphs
- Output ONLY the format below
- Keep explanations short

Compliance Findings:
{compliance}

FORMAT:

LEGAL RISK 1
Clause:
Risk Type:
Risk Level:
Recommendation:

LEGAL RISK 2
Clause:
Risk Type:
Risk Level:
Recommendation:

LEGAL RISK 3
Clause:
Risk Type:
Risk Level:
Recommendation:

Contract:
{contract}
"""

    response = llm.invoke(prompt)

    return {"legal_result": response.content}


# ---------------- FINANCE AGENT ----------------

def finance_agent(state):

    compliance = state["compliance_result"]
    legal = state["legal_result"]

    prompt = f"""
You are a financial risk analyst.

Use compliance and legal findings to identify TOP 3 financial risks.

STRICT RULES:
- No paragraphs
- Short answers only
- Follow format strictly

Compliance Findings:
{compliance}

Legal Issues:
{legal}

FORMAT:

FINANCIAL RISK 1
Clause:
Risk Type:
Risk Level:
Recommendation:

FINANCIAL RISK 2
Clause:
Risk Type:
Risk Level:
Recommendation:

FINANCIAL RISK 3
Clause:
Risk Type:
Risk Level:
Recommendation:
"""

    response = llm.invoke(prompt)

    return {"finance_result": response.content}


# ---------------- OPERATIONS AGENT ----------------

def operations_agent(state):

    compliance = state["compliance_result"]
    legal = state["legal_result"]
    finance = state["finance_result"]

    prompt = f"""
You are an operations risk analyst.

Use previous agent findings to identify TOP 3 operational risks.

STRICT RULES:
- No paragraphs
- Only structured format

Compliance Findings:
{compliance}

Legal Issues:
{legal}

Financial Risks:
{finance}

FORMAT:


OPERATIONS RISK 1
Clause:
Risk Type:
Risk Level:
Recommendation:

OPERATIONS RISK 2
Clause:
Risk Type:
Risk Level:
Recommendation:

OPERATIONS RISK 3
Clause:
Risk Type:
Risk Level:
Recommendation:
"""

    response = llm.invoke(prompt)

    return {"operations_result": response.content}