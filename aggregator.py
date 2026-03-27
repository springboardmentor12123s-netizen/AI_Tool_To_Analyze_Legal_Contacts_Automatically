from prompt_templates import SUMMARY_PROMPT
from llm_setup import analysis_llm
from risk_scoring import calculate_risk_score
import uuid

# Optional (Milestone 3 - Pinecone)
try:
    from vector_store import store_data
except:
    store_data = None


def aggregate_results(planning_result, agent_results):

    final_output = {}

    # ----------------------------
    # Planning Result
    # ----------------------------
    final_output["Planning Result"] = f"""
Domains Selected: {planning_result.get("domains")}

Confidence: {planning_result.get("confidence")}

Reason: {planning_result.get("reason")}
"""

    # ----------------------------
    # Agent Results (Structured)
    # ----------------------------
    combined_text_list = []

    for agent, result in agent_results.items():
        analysis_text = result.get("raw", "No result")

        clean_text = analysis_text.replace("*", "").strip()

        final_output[f"{agent.capitalize()} Analysis"] = clean_text

        combined_text_list.append(clean_text)

    combined_text = "\n".join(combined_text_list)

    # ----------------------------
    # Multi-turn Refinement (Milestone 3)
    # ----------------------------
    REFINE_PROMPT = """
Refine and improve this combined analysis:

{text}
"""

    try:
        refined_output = analysis_llm.invoke(
            REFINE_PROMPT.format(text=combined_text)
        ).content
    except Exception:
        refined_output = combined_text  # fallback

    # ----------------------------
    # Final Summary Generation
    # ----------------------------
    try:
        if not refined_output.strip():
            refined_output = combined_text

        summary = analysis_llm.invoke(
            SUMMARY_PROMPT.format(text=refined_output)
        ).content

    except Exception as e:
        print("Summary Error:", e)
        summary = "Executive summary could not be generated, but analysis is complete."

    final_output["Summary"] = summary

    # ----------------------------
    # Risk Score (New Feature)
    # ----------------------------
    risk_score = calculate_risk_score(refined_output)
    final_output["Risk Score"] = f"{risk_score}/100"

    # ----------------------------
    # Store in Pinecone (Milestone 3)
    # ----------------------------
    if store_data:
        try:
            doc_id = str(uuid.uuid4())
            store_data(doc_id, refined_output)
        except Exception as e:
            print("Pinecone storage failed:", e)

    print("Aggregation complete")

    return final_output


def aggregation_node(state: dict):

    planning_result = state["planning_result"]
    agent_results = state["agent_results"]

    final = aggregate_results(planning_result, agent_results)

    return {
        "final_report": final
    }