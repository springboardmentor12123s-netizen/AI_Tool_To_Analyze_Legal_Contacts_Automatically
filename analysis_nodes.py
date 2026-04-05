from llm_setup import gemini_llm, groq_llm
from vector_store import retrieve_similar


# ============================================
# 🔥 SAFE TEXT LIMITER (VERY IMPORTANT)
# ============================================
def safe_limit(text, max_chars=3000):
    if not text:
        return ""
    return text[:max_chars]


# ============================================
# 🔥 SMART CONTEXT BUILDER (RAG CONTROL)
# ============================================
def build_context(text):
    try:
        chunks = retrieve_similar(text)

        # Take top 3 chunks only
        selected = chunks[:3]

        context = "\n".join(selected)

        return safe_limit(context, 1500)

    except:
        return ""


# ============================================
# 🔥 LEGAL AGENT
# ============================================
def legal_agent(text):

    contract = safe_limit(text, 3000)
    context = build_context(text)

    prompt = f"""
You are an expert Legal Contract Analyzer.

Your job is to find REAL risks in the contract.

STRICT RULES:
- NEVER say "contract not provided"
- ALWAYS analyze given contract
- DO NOT give generic answers
- Be specific and practical

FORMAT:
1. Clause: "<exact clause from contract>"
   Risk: <clear explanation>

2. Clause: "<exact clause>"
   Risk: <issue>

Check:
- Missing clauses
- Liability issues
- Ambiguity

CONTRACT:
{contract}

REFERENCE CONTEXT:
{context}
"""

    try:
        response = groq_llm.invoke(prompt).content
        return {"Legal Analysis": response}
    except Exception as e:
        return {"Legal Analysis": f"Error: {str(e)}"}


# ============================================
# 🔥 FINANCE AGENT
# ============================================
def finance_agent(text):

    contract = safe_limit(text, 3000)
    context = build_context(text)

    prompt = f"""
You are a Financial Risk Analyzer.

Analyze financial risks in the contract.

STRICT RULES:
- DO NOT ask for contract again
- USE given contract only
- Give practical risks

FORMAT:
1. Clause: "<text>"
   Risk: <issue>

Check:
- Payment terms
- Penalties
- Cost risks

CONTRACT:
{contract}

REFERENCE:
{context}
"""

    try:
        response = gemini_llm.invoke(prompt).content
        return {"Finance Analysis": response}
    except Exception as e:
        return {"Finance Analysis": f"Error: {str(e)}"}


# ============================================
# 🔥 COMPLIANCE AGENT
# ============================================
def compliance_agent(text):

    contract = safe_limit(text, 3000)
    context = build_context(text)

    prompt = f"""
You are a Compliance Risk Analyzer.

Analyze compliance risks in the contract.

STRICT RULES:
- NEVER say "not provided"
- USE given contract
- Be specific

FORMAT:
1. Clause: "<text>"
   Risk: <issue>

Check:
- Data protection
- Legal compliance
- Regulatory gaps

CONTRACT:
{contract}

REFERENCE:
{context}
"""

    try:
        response = groq_llm.invoke(prompt).content
        return {"Compliance Analysis": response}
    except Exception as e:
        return {"Compliance Analysis": f"Error: {str(e)}"}


# ============================================
# 🔥 EXECUTION NODE (IMPORTANT)
# ============================================
def execute_agents_node(state: dict):

    text = state["contract_text"]
    planning = state.get("planning_result", {})

    execution_order = planning.get("execution_order", [])

    results = {}

    if "legal" in execution_order:
        results["legal"] = legal_agent(text)

    if "finance" in execution_order:
        results["finance"] = finance_agent(text)

    if "compliance" in execution_order:
        results["compliance"] = compliance_agent(text)

    return {"agent_results": results}
