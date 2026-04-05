from prompt_templates import *
from llm_setup import gemini_llm, groq_llm
from vector_store import retrieve_similar


# ============================================
# 🔥 SMART TOKEN LIMITER (IMPORTANT)
# ============================================
def limit_text_by_size(text_list, max_chars=4000):
    final_text = ""

    for chunk in text_list:
        if len(final_text) + len(chunk) > max_chars:
            break
        final_text += chunk + "\n"

    return final_text


# ============================================
# LEGAL AGENT
# ============================================
def legal_agent(text):

    context_list = retrieve_similar(text)
    context = limit_text_by_size(context_list, max_chars=4000)

    prompt = f"""
    Analyze legal risks in this contract.

    IMPORTANT:
    - For each risk, mention the EXACT clause line causing it
    - Format strictly:

    1. Clause: "<copy exact clause text>"
       Risk: <explain issue>

    2. Clause: "<clause>"
       Risk: <issue>

    ONLY USE BELOW CLAUSES:
    {context}
    """

    try:
        response = groq_llm.invoke(prompt).content
        return {"Legal Analysis": response}
    except Exception as e:
        return {"Legal Analysis": f"Error: {str(e)}"}


# ============================================
# FINANCE AGENT
# ============================================
def finance_agent(text):

    context_list = retrieve_similar(text)
    context = limit_text_by_size(context_list, max_chars=4000)

    prompt = f"""
    Analyze financial risks.

    Format:
    1. Clause: "<text>"
       Risk: <issue>

    Check:
    - payment terms
    - penalties
    - cost risks

    ONLY USE BELOW CLAUSES:
    {context}
    """

    try:
        response = gemini_llm.invoke(prompt).content
        return {"Finance Analysis": response}
    except Exception as e:
        return {"Finance Analysis": f"Error: {str(e)}"}


# ============================================
# COMPLIANCE AGENT
# ============================================
def compliance_agent(text):

    context_list = retrieve_similar(text)
    context = limit_text_by_size(context_list, max_chars=4000)

    prompt = f"""
    Analyze compliance risks.

    Format:
    1. Clause: "<text>"
       Risk: <issue>

    Check:
    - data protection
    - regulatory gaps

    ONLY USE BELOW CLAUSES:
    {context}
    """

    try:
        response = groq_llm.invoke(prompt).content
        return {"Compliance Analysis": response}
    except Exception as e:
        return {"Compliance Analysis": f"Error: {str(e)}"}


# ============================================
# NEW: OPERATIONS AGENT
# ============================================
def operations_agent(text):

    context_list = retrieve_similar(text)
    context = limit_text_by_size(context_list, max_chars=4000)

    prompt = f"""
    Analyze operational risks.

    Format:
    1. Clause: "<text>"
       Risk: <issue>

    Check:
    - delivery timelines
    - SLA gaps
    - resourcing issues
    - project feasibility

    ONLY USE BELOW CLAUSES:
    {context}
    """

    try:
        response = gemini_llm.invoke(prompt).content
        return {"Operations Analysis": response}
    except Exception as e:
        return {"Operations Analysis": f"Error: {str(e)}"}
