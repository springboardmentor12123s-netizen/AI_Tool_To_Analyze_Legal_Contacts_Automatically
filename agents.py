from prompt_templates import *
from llm_setup import analysis_llm


def legal_agent(text):
    print("Legal agent thinking...")
    try:
        response = analysis_llm.invoke(LEGAL_PROMPT.format(text=text)).content

        return {
            "agent": "legal",
            "risks": response.split("\n"),
            "raw": response
        }

    except Exception as e:
        print("Legal agent error:", e)
        return {
            "agent": "legal",
            "risks": [],
            "raw": "Legal analysis failed due to API limit or error."
        }


def finance_agent(text):
    print("Finance agent thinking...")
    try:
        response = analysis_llm.invoke(FINANCE_PROMPT.format(text=text)).content

        return {
            "agent": "finance",
            "risks": response.split("\n"),
            "raw": response
        }

    except Exception as e:
        print("Finance agent error:", e)
        return {
            "agent": "finance",
            "risks": [],
            "raw": "Financial analysis failed due to API limit or error."
        }


def compliance_agent(text):
    print("Compliance agent thinking...")
    try:
        response = analysis_llm.invoke(COMPLIANCE_PROMPT.format(text=text)).content

        return {
            "agent": "compliance",
            "risks": response.split("\n"),
            "raw": response
        }

    except Exception as e:
        print("Compliance agent error:", e)
        return {
            "agent": "compliance",
            "risks": [],
            "raw": "Compliance analysis failed due to API limit or error."
        }