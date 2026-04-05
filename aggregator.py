from prompt_templates import SUMMARY_PROMPT
from llm_setup import analysis_llm
from risk_scoring import calculate_risk_score
import uuid

def aggregate_results(planning_result, agent_results):

    final_output = {}

    # ----------------------------
    # Planning Result (SAFE FIX)
    # ----------------------------
    if isinstance(planning_result, dict):
        reason = planning_result.get("reason", "Not Available")
        confidence = planning_result.get("confidence", 0)
    else:
        reason = str(planning_result)
        confidence = 0.9  # default fallback

    final_output["Planning Result"] = f"""
Reason: {reason}
"""

    # ----------------------------
    # ADD CONFIDENCE (FIX)
    # ----------------------------
    try:
        confidence_percent = int(float(confidence) * 100)
    except:
        confidence_percent = 90

    final_output["Confidence"] = confidence_percent

    # ----------------------------
    # Agent Results (FIXED)
    # ----------------------------
    combined_text_list = []

    for agent, result in agent_results.items():

        # ✅ FIX: HANDLE BOTH dict AND str
        if isinstance(result, dict):
            analysis_text = (
                result.get("Legal Analysis") or
                result.get("Finance Analysis") or
                result.get("Compliance Analysis") or
                "No result"
            )
        elif isinstance(result, str):
            analysis_text = result
        else:
            analysis_text = "No result"

        clean_text = str(analysis_text).replace("*", "").strip()

        final_output[f"{agent.capitalize()} Analysis"] = clean_text
        combined_text_list.append(clean_text)

    combined_text = "\n".join(combined_text_list)

    # ----------------------------
    # Refinement (SAFE)
    # ----------------------------
    try:
        refined_output = analysis_llm.invoke(
            f"Refine and improve this:\n{combined_text[:3000]}"
        ).content
    except:
        refined_output = combined_text

    # ----------------------------
    # Summary
    # ----------------------------
    try:
        summary = analysis_llm.invoke(
            SUMMARY_PROMPT.format(text=refined_output[:3000])
        ).content
    except:
        summary = "Summary could not be generated."

    final_output["Summary"] = summary

    # ----------------------------
    # Risk Score
    # ----------------------------
    try:
        risk_score = calculate_risk_score(refined_output)
    except:
        risk_score = 50

    final_output["Risk Score"] = f"{risk_score}/100"

    print("Aggregation complete")

    return final_output


def aggregation_node(state: dict):
    planning_result = state["planning_result"]
    agent_results = state["agent_results"]

    final = aggregate_results(planning_result, agent_results)

    return {
        "final_report": final
    }
