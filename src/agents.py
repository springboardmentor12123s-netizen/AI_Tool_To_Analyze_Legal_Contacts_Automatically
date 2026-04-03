from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

# USE the powerful 70b model for high accuracy instead of 8b-instant
llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.15,
    max_tokens=500,
)


# ---------------- COMPLIANCE AGENT ----------------

def compliance_agent(state):
    contract = state["contract"]

    prompt = f"""You are an expert compliance risk analyst with deep regulatory knowledge.

Analyze this contract and identify the TOP 3 compliance risks with HIGH ACCURACY.

RULES:
- Read the ENTIRE contract before answering
- Quote exact clause text as evidence
- Always cite the exact clause or section from the document. Never give vague or generic analysis.
- Do NOT hallucinate - only cite what exists
- If a risk area has no issues, say "No compliance risk identified"
- Be precise about regulatory frameworks (GDPR, HIPAA, SOX, etc.)

FORMAT (strictly follow):

COMPLIANCE RISK 1
Clause: [exact quote from contract]
Risk Type: [specific regulatory risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

COMPLIANCE RISK 2
Clause: [exact quote from contract]
Risk Type: [specific regulatory risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

COMPLIANCE RISK 3
Clause: [exact quote from contract]
Risk Type: [specific regulatory risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

Contract:
{contract}"""

    response = llm.invoke(prompt)
    return {"compliance_result": response.content}


# ---------------- LEGAL AGENT ----------------

def legal_agent(state):
    contract = state["contract"]
    compliance = state["compliance_result"]

    prompt = f"""You are a senior legal contract analyst.

Using the compliance findings AND the original contract, identify the TOP 3 legal risks.

RULES:
- Cross-reference compliance findings with contract text
- Quote exact clauses as evidence
- Always cite the exact clause or section from the document. Never give vague or generic analysis.
- Focus on enforceability, liability, dispute resolution, termination rights
- Do NOT repeat compliance findings - find NEW legal issues
- Do NOT hallucinate

Compliance Findings:
{compliance}

FORMAT (strictly follow):

LEGAL RISK 1
Clause: [exact quote from contract]
Risk Type: [specific legal risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

LEGAL RISK 2
Clause: [exact quote from contract]
Risk Type: [specific legal risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

LEGAL RISK 3
Clause: [exact quote from contract]
Risk Type: [specific legal risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

Contract:
{contract}"""

    response = llm.invoke(prompt)
    return {"legal_result": response.content}


# ---------------- FINANCE AGENT ----------------

def finance_agent(state):
    compliance = state["compliance_result"]
    legal = state["legal_result"]
    contract = state.get("contract", "")

    prompt = f"""You are a senior financial risk analyst.

Using compliance and legal findings AND the original contract, identify TOP 3 financial risks.

RULES:
- Focus on payment terms, penalties, liability caps, cost exposure, termination fees
- Quote exact monetary figures and percentages from the contract
- Always cite the exact clause or section from the document. Never give vague or generic analysis.
- Do NOT repeat compliance or legal findings - find NEW financial issues
- Do NOT hallucinate - only cite what exists in the contract

Compliance Findings:
{compliance}

Legal Issues:
{legal}

FORMAT (strictly follow):

FINANCIAL RISK 1
Clause: [exact quote from contract]
Risk Type: [specific financial risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

FINANCIAL RISK 2
Clause: [exact quote from contract]
Risk Type: [specific financial risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

FINANCIAL RISK 3
Clause: [exact quote from contract]
Risk Type: [specific financial risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

Contract:
{contract}"""

    response = llm.invoke(prompt)
    return {"finance_result": response.content}


# ---------------- OPERATIONS AGENT ----------------

def operations_agent(state):
    compliance = state["compliance_result"]
    legal = state["legal_result"]
    finance = state["finance_result"]
    contract = state.get("contract", "")

    prompt = f"""You are a senior operations risk analyst.

Using all previous agent findings AND the original contract, identify TOP 3 operational risks.

RULES:
- Focus on SLAs, delivery timelines, resource dependencies, escalation paths
- Quote exact clauses as evidence
- Always cite the exact clause or section from the document. Never give vague or generic analysis.
- Do NOT repeat findings from other agents - find NEW operational issues
- Do NOT hallucinate

Compliance Findings:
{compliance}

Legal Issues:
{legal}

Financial Risks:
{finance}

FORMAT (strictly follow):

OPERATIONS RISK 1
Clause: [exact quote from contract]
Risk Type: [specific operational risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

OPERATIONS RISK 2
Clause: [exact quote from contract]
Risk Type: [specific operational risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

OPERATIONS RISK 3
Clause: [exact quote from contract]
Risk Type: [specific operational risk]
Risk Level: High / Medium / Low
Recommendation: [specific actionable fix]

Contract:
{contract}"""

    response = llm.invoke(prompt)
    return {"operations_result": response.content}
