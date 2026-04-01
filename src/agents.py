import json
import time

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    max_tokens=800,
)


AGENT_CONFIG = {
    "compliance": {
        "result_key": "compliance_result",
        "role": "Compliance analyst",
        "focus": "regulatory obligations, privacy, consent, audits, data handling, retention, and security commitments",
        "prior": [],
    },
    "legal": {
        "result_key": "legal_result",
        "role": "Legal analyst",
        "focus": "liability, indemnity, warranties, jurisdiction, dispute resolution, termination, and enforceability",
        "prior": [("Compliance", "compliance_result")],
    },
    "finance": {
        "result_key": "finance_result",
        "role": "Finance analyst",
        "focus": "pricing, payment timing, penalties, taxes, invoicing, reimbursement, and budget exposure",
        "prior": [("Compliance", "compliance_result"), ("Legal", "legal_result")],
    },
    "operations": {
        "result_key": "operations_result",
        "role": "Operations analyst",
        "focus": "deliverables, timelines, dependencies, service levels, handoffs, resourcing, and execution feasibility",
        "prior": [
            ("Compliance", "compliance_result"),
            ("Legal", "legal_result"),
            ("Finance", "finance_result"),
        ],
    },
}


def safe_invoke(prompt):
    from groq import RateLimitError

    for _ in range(3):
        try:
            return llm.invoke(prompt)
        except RateLimitError:
            time.sleep(2)
    return None


def _normalize_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip(" -*") for line in value.splitlines() if line.strip(" -*")]
    return [str(value).strip()]


def _fallback_result(text, default_summary):
    cleaned = text.strip() if text else ""
    return {
        "summary": cleaned or default_summary,
        "risks": [],
        "recommendations": [],
    }


def parse_structured_response(response, default_summary):
    content = getattr(response, "content", "") if response else ""
    if not content:
        return _fallback_result("", default_summary)

    raw_text = content.strip()
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return _fallback_result(raw_text, default_summary)

    try:
        parsed = json.loads(raw_text[start : end + 1])
    except json.JSONDecodeError:
        return _fallback_result(raw_text, default_summary)

    if not isinstance(parsed, dict):
        return _fallback_result(raw_text, default_summary)

    return {
        "summary": str(
            parsed.get("summary")
            or parsed.get("analysis")
            or parsed.get("overview")
            or default_summary
        ).strip(),
        "risks": _normalize_list(parsed.get("risks")),
        "recommendations": _normalize_list(parsed.get("recommendations")),
    }


def serialize_agent_result(result):
    summary = result.get("summary", "")
    risks = result.get("risks", [])
    recommendations = result.get("recommendations", [])

    lines = [f"Summary: {summary}", "Risks:"]
    lines.extend(f"- {risk}" for risk in risks) if risks else lines.append("- None identified")
    lines.append("Recommendations:")
    lines.extend(f"- {item}" for item in recommendations) if recommendations else lines.append("- None provided")
    return "\n".join(lines)


def serialize_report_context(result):
    summary = result.get("summary", "")
    risks = result.get("risks", [])

    lines = [f"Summary: {summary}", "Risks:"]
    lines.extend(f"- {risk}" for risk in risks) if risks else lines.append("- None identified")
    return "\n".join(lines)


def build_agent_prompt(agent_name, state):
    config = AGENT_CONFIG[agent_name]
    contract = state["contract"]
    tone = state.get("tone", "professional").lower()
    focus = state.get("focus", "All")

    prior_blocks = []
    for label, key in config["prior"]:
        prior_blocks.append(f"{label}:\n{serialize_agent_result(state[key])}")

    prior_context = ""
    if prior_blocks:
        prior_context = "\n\nPrevious findings:\n" + "\n\n".join(prior_blocks) + """

Use previous findings as context only.
Do not repeat them word for word.
Add new insight from your own specialty.
"""

    return f"""
You are a {config["role"]} reviewing a contract.

Return valid JSON only with:
{{
  "summary": "brief analysis",
  "risks": ["main risk point"],
  "recommendations": ["main recommendation point"]
}}

Keep the response concise and {tone}.
Focus only on {config["focus"]}.
Use the selected focus area "{focus}" when it overlaps with your specialty.
Return only the main simple points.
Do not force a fixed number of risks or recommendations.
If there are no meaningful risks or recommendations, return an empty list.

Contract:
{contract}{prior_context}
"""


def run_agent(agent_name, state):
    config = AGENT_CONFIG[agent_name]
    prompt = build_agent_prompt(agent_name, state)
    response = safe_invoke(prompt)
    default_summary = f"{config['role']} review could not be structured, so raw output was preserved."
    return {config["result_key"]: parse_structured_response(response, default_summary)}


def compliance_agent(state):
    return run_agent("compliance", state)


def legal_agent(state):
    return run_agent("legal", state)


def finance_agent(state):
    return run_agent("finance", state)


def operations_agent(state):
    return run_agent("operations", state)


def report_generator(state):
    contract = state["contract"]
    prompt = f"""
Generate FINAL REPORT.

IMPORTANT:
- Do not copy the agent results word for word
- Use the contract plus the specialized findings below
- Keep it simple and clear
- No long paragraphs

Specialized findings:

Compliance:
{serialize_report_context(state["compliance_result"])}

Legal:
{serialize_report_context(state["legal_result"])}

Finance:
{serialize_report_context(state["finance_result"])}

Operations:
{serialize_report_context(state["operations_result"])}

FORMAT:

OVERALL ANALYSIS:
- Provide 4-5 simple points describing the contract

KEY RISKS:
- Provide general risks from contract with severity

RECOMMENDATIONS:
- Provide only a few high-level overall contract improvement suggestions
- Do not include all agent recommendation points
- Keep this section short

Contract:
{contract}
"""

    response = safe_invoke(prompt)
    final_report = response.content if response and getattr(response, "content", None) else ""
    return {
        "final_report": final_report or "Final report could not be generated at this time."
    }
