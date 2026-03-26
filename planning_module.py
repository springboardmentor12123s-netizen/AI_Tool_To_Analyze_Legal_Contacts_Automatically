import json
import re
from llm_setup import planning_llm
def planning_agent(text):

    print("Step 1: Planning domains")

    prompt = f"""
Identify required domains from: legal, finance, compliance.
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

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", response, re.DOTALL)

        if json_match:
            plan = json.loads(json_match.group())
        else:
            raise Exception("No JSON found")

        print("Planning Result:", plan)
        return plan

    except Exception as e:
        print("Planning failed:", e)

        # fallback plan
        return {
            "domains": ["legal"],
            "confidence": 0.5,
            "execution_order": ["legal"],
            "reason": "Fallback planning"
        }

def planning_node(state: dict):

    text = state["contract_text"]
    plan = planning_agent(text)

    return {
        "planning_result": plan
    }