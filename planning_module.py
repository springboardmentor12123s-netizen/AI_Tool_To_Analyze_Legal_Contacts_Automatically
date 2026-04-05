import json
import re
from llm_setup import gemini_llm as planning_llm


def planning_agent(text):
    print("Step 1: Planning domains")

    prompt = f"""
    Identify required domains from: legal, finance, compliance, operations.

    Return JSON only:
    {{
        "domains": [],
        "confidence": 0-1,
        "execution_order": [],
        "reason": ""
    }}

    Contract:
    {text}
    """

    try:
        response = planning_llm.invoke(prompt).content
        print("Raw LLM Response:", response)

        json_match = re.search(r"\\{.*\\}", response, re.DOTALL)

        if json_match:
            plan = json.loads(json_match.group())
        else:
            raise Exception("No JSON found")

        # Ensure operations domain is considered
        # If LLM forgets, we add it manually
        available_domains = ["legal", "finance", "compliance", "operations"]

        extracted = plan.get("domains", [])
        fixed_domains = list({*extracted, *available_domains})  # avoid duplicates
        plan["domains"] = fixed_domains

        # Fix execution_order if missing
        if not plan.get("execution_order"):
            plan["execution_order"] = fixed_domains

        print("Planning Result:", plan)
        return plan

    except Exception as e:
        print("Planning failed:", e)

        return {
            "domains": ["legal", "finance", "compliance", "operations"],
            "confidence": 0.5,
            "execution_order": ["legal", "finance", "compliance", "operations"],
            "reason": "Fallback planning"
        }


def planning_node(state: dict):
    text = state["contract_text"]
    plan = planning_agent(text)
    return {"planning_result": plan}
