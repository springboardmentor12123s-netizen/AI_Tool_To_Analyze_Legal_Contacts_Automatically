from langchain_groq import ChatGroq
from dotenv import load_dotenv
import time

load_dotenv()

# -------- LLM --------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=800
)

# -------- SAFE INVOKE --------
def safe_invoke(prompt):
    from groq import RateLimitError

    for _ in range(3):
        try:
            return llm.invoke(prompt)
        except RateLimitError:
            time.sleep(2)
    return None


# -------- COMPLIANCE AGENT --------
def compliance_agent(state):
    contract = state["contract"]

    prompt = f"""
Identify TOP 3 compliance risks.

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

    response = safe_invoke(prompt)

    return {"compliance_result": response.content}


# -------- LEGAL AGENT --------
def legal_agent(state):
    contract = state["contract"]
    compliance = state["compliance_result"]

    prompt = f"""
Using contract and compliance findings:

{compliance}

Identify TOP 3 legal risks.

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

    response = safe_invoke(prompt)

    return {"legal_result": response.content}


# -------- FINANCE AGENT --------
def finance_agent(state):
    compliance = state["compliance_result"]
    legal = state["legal_result"]

    prompt = f"""
Using findings:

Compliance:
{compliance}

Legal:
{legal}

Identify TOP 3 financial risks.

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

    response = safe_invoke(prompt)

    return {"finance_result": response.content}


# -------- OPERATIONS AGENT --------
def operations_agent(state):
    compliance = state["compliance_result"]
    legal = state["legal_result"]
    finance = state["finance_result"]

    prompt = f"""
Using all findings:

Compliance:
{compliance}

Legal:
{legal}

Finance:
{finance}

Identify TOP 3 operational risks.

FORMAT:

OPERATIONAL RISK 1
Clause:
Risk Type:
Risk Level:
Recommendation:

OPERATIONAL RISK 2
Clause:
Risk Type:
Risk Level:
Recommendation:

OPERATIONAL RISK 3
Clause:
Risk Type:
Risk Level:
Recommendation:
"""

    response = safe_invoke(prompt)

    return {"operations_result": response.content}


# -------- FINAL REPORT --------
def report_generator(state):

    contract = state["contract"]

    prompt = f"""
Generate FINAL REPORT.

IMPORTANT:
- Do NOT copy risks from agent outputs
- Generate risks based on overall contract understanding
- Keep it simple and clear
- No paragraphs

FORMAT:

OVERALL ANALYSIS:
- Provide 4–5 simple points describing the contract

KEY RISKS:
- Provide general risks from contract (with level)

RECOMMENDATIONS:
- Provide overall contract improvement suggestions

Contract:
{contract}
"""

    response = safe_invoke(prompt)

    return {"final_report": response.content}