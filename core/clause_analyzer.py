import hashlib
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Callable, Optional

from core.document_loader import chunk_contract_text, parse_contract_text
from core.llm_engine import (
    ANALYST_ROLES,
    get_llm_response,
    index_contract_chunks,
    retrieve_analysis_artifact,
    retrieve_context,
    run_role_agent,
    store_analysis_artifact,
    USE_LOCAL_LLM,
    vectorstore_available,
)
from core.planning_module import build_agent_execution_plan
from utils.prompts import (
    build_clause_extraction_prompt,
    build_direct_analysis_prompt,
    build_evidence_extraction_prompt,
    build_fast_summary_prompt,
    build_synthesis_prompt,
    build_turbo_analysis_prompt,
)


CACHE_VERSION = os.getenv("CLAUSEAI_CACHE_VERSION", "6")
AGENT_OUTPUT_FORMAT_VERSION = "2"


# Parse integer env values safely so bad config does not break analysis.
def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        return max(minimum, int(raw))
    except (TypeError, ValueError):
        return max(minimum, default)


def _stable_doc_id(contract_text: str) -> str:
    normalized = (contract_text or "").strip()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"doc-{digest[:24]}"


def _hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:16]


@lru_cache(maxsize=64)
def _prepare_contract_inputs(contract_text: str) -> dict:
    normalized_text = contract_text or ""
    model_char_limit = _env_int("CLAUSEAI_MODEL_CHAR_LIMIT", 14000, minimum=2000)
    agent_char_limit = _env_int("CLAUSEAI_AGENT_CHAR_LIMIT", 10000, minimum=1500)
    return {
        "contract_text": normalized_text,
        "contract_text_for_model": _build_prompt_contract_text(normalized_text, model_char_limit),
        "contract_text_for_agents": _build_prompt_contract_text(normalized_text, agent_char_limit),
        "doc_id": _stable_doc_id(normalized_text),
        "evidence_signals": _rule_based_clause_signals(normalized_text),
        "index_chunks": tuple(chunk_contract_text(normalized_text, chunk_size=2500, chunk_overlap=300)[:8]),
    }


def _cache_key(doc_id: str, stage: str, **parts: object) -> str:
    normalized_parts = [f"v={CACHE_VERSION}", f"doc={doc_id}", f"stage={stage}"]
    for key in sorted(parts):
        normalized_parts.append(f"{key}={parts[key]}")
    return "|".join(normalized_parts)


def _extract_snippet(text: str, pattern: str, flags: int = re.IGNORECASE, radius: int = 140) -> str:
    source = text or ""
    match = re.search(pattern, source, flags)
    if not match:
        return ""
    start = max(0, match.start() - radius)
    end = min(len(source), match.end() + radius)
    snippet = re.sub(r"\s+", " ", source[start:end]).strip()
    return snippet[:320] + ("..." if len(snippet) > 320 else "")


def _build_prompt_contract_text(text: str, char_limit: int) -> str:
    source = (text or "").strip()
    if len(source) <= char_limit:
        return source

    head_size = int(char_limit * 0.40)
    middle_size = int(char_limit * 0.30)
    tail_size = char_limit - head_size - middle_size

    sections = [source[:head_size].strip()]

    if middle_size > 0:
        middle_start = max(0, (len(source) // 2) - (middle_size // 2))
        middle = source[middle_start:middle_start + middle_size].strip()
        if middle and middle != sections[0]:
            sections.append(middle)

    if tail_size > 0:
        tail = source[-tail_size:].strip()
        if tail and tail not in sections:
            sections.append(tail)

    result = "\n\n[...document continues...]\n\n".join(
        section for section in sections if section
    ).strip()
    return result[:char_limit].strip()


def _rule_based_clause_signals(contract_text: str) -> str:
    source = contract_text or ""
    checks = [
        ("Payment terms", r"\b(payment|invoice|fees?|pricing|late payment)\b"),
        ("Termination", r"\b(terminate|termination|breach|for cause|for convenience)\b"),
        ("Liability", r"\b(liability|liable|limitation of liability|damages)\b"),
        ("Indemnity", r"\b(indemnif\w+)\b"),
        ("Confidentiality", r"\b(confidential|non-disclosure|nda)\b"),
        ("Governing law", r"\b(governing law|laws of|jurisdiction|venue|arbitration|dispute resolution)\b"),
        ("Data privacy", r"\b(gdpr|hipaa|privacy|personal data|data protection|security)\b"),
        ("Service levels", r"\b(sla|service levels?|uptime|response time|availability)\b"),
    ]
    lines = []
    for label, pattern in checks:
        snippet = _extract_snippet(source, pattern)
        if snippet:
            lines.append(f"- {label}: {snippet}")
    return "\n".join(lines)


def _is_placeholder_text(text: str) -> bool:
    value = re.sub(r"\s+", " ", (text or "").strip(" -.:")).lower()
    if not value:
        return True
    placeholders = {
        "not stated",
        "not available",
        "none stated",
        "n/a",
        "na",
        "unknown",
        "tbd",
        "not generated",
        "auto-detected from uploaded analysis",
        "auto-detected from uploaded contract analysis",
        "further review recommended",
    }
    if value in placeholders:
        return True
    return value.startswith("not generated because") or value.startswith("not generated due to")


def _normalize_output_item(text: str) -> str:
    value = re.sub(r"\s+", " ", (text or "").strip())
    value = value.lstrip("-").strip()
    value = value.rstrip(". ")
    if not value or _is_placeholder_text(value) or _is_incomplete_bullet(value):
        return ""
    return value


def _prepare_output_bullets(items, limit: int = 4) -> list[str]:
    cleaned = []
    seen = set()
    for item in items or []:
        normalized = _normalize_output_item(item)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        if normalized[-1] not in ".!?":
            normalized += "."
        cleaned.append(f"- {normalized}")
        if len(cleaned) >= limit:
            break
    return cleaned


def _extract_candidate_sentences(text: str, limit: int = 4) -> list[str]:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized or _is_placeholder_text(normalized):
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    results = []
    seen = set()
    for part in parts:
        cleaned = _normalize_output_item(part)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(cleaned)
        if len(results) >= limit:
            break
    return results


def _extract_validated_key_fields(contract_text: str, doc_id: str) -> str:
    cache_key = _cache_key(doc_id, "validated_key_fields", text_sig=_hash_text(contract_text))
    cached = retrieve_analysis_artifact(cache_key)
    if isinstance(cached, str) and cached.strip():
        return cached

    prompt = build_evidence_extraction_prompt(contract_text)
    result = get_llm_response(prompt, num_predict=600)
    cleaned = (result or "").strip()
    if cleaned:
        store_analysis_artifact(cache_key, cleaned)
    return cleaned


def _default_section_message(section_name: str) -> str:
    defaults = {
        "Findings": "- No role-specific finding was clearly supported by the extracted text.",
        "Risks": "- No material role-specific risk was clearly supported by the extracted text.",
        "Missing / Weak points": "- No role-specific missing protection was clearly supported by the extracted text.",
        "Recommended follow-up actions": "- Review the highlighted clauses and confirm whether additional role-specific protections are needed.",
        "Key Clauses": "- No material clause could be confirmed from the available analysis text.",
        "Missing / Weak": "- No clearly missing or weak clause was identified from the available analysis text.",
    }
    return defaults.get(section_name, "- No additional supported detail was available.")


def _is_incomplete_bullet(text: str) -> bool:
    value = (text or "").strip()
    if not value:
        return True
    bad_suffixes = ("...", "..", "the....", "the...", "and", "or", "to", "for", "with", "without", "of", "the")
    trailing_terms = (" and", " or", " to", " for", " with", " without", " of", " the", " a", " an")
    lowered = value.lower().rstrip(". ")
    if value.endswith("...") or value.endswith(".."):
        return True
    if lowered in bad_suffixes:
        return True
    return any(lowered.endswith(term) for term in trailing_terms)


def _derive_follow_up_action(issue: str) -> str:
    normalized = re.sub(r"\s+", " ", (issue or "").strip(" -.:"))
    if not normalized:
        return "Review the document for any unresolved issue."
    lowered = normalized.lower()
    if lowered.startswith("the contract does not include"):
        remainder = normalized[len("The contract does not include"):].strip(" .")
        return f"Add {remainder.lower()} to the contract."
    if lowered.startswith("the contract does not explicitly state"):
        remainder = normalized[len("The contract does not explicitly state"):].strip(" .")
        return f"Clarify {remainder.lower()} in the contract."
    if lowered.startswith("the contract does not specify"):
        remainder = normalized[len("The contract does not specify"):].strip(" .")
        return f"Specify {remainder.lower()} in the contract."
    if lowered.startswith("the contract does not define"):
        remainder = normalized[len("The contract does not define"):].strip(" .")
        return f"Define {remainder.lower()} in the contract."
    if lowered.startswith("the contract lacks"):
        remainder = normalized[len("The contract lacks"):].strip(" .")
        return f"Add {remainder.lower()} to the contract."
    if lowered.startswith("missing "):
        return f"Address the missing item: {normalized.rstrip('.')}."
    if lowered.startswith("unclear "):
        return f"Clarify {normalized[8:].strip().rstrip('.').lower()}."
    return f"Address this issue in the contract: {normalized.rstrip('.')}."


def _build_agent_section_fallbacks(sections: dict, body: str = "") -> dict:
    findings = _prepare_output_bullets(sections.get("Findings", []) or [])
    risks = _prepare_output_bullets(sections.get("Risks", []) or [])
    missing_points = _prepare_output_bullets(sections.get("Missing / Weak points", []) or [])
    recommended_actions = _prepare_output_bullets(sections.get("Recommended follow-up actions", []) or [])

    candidate_issues = []
    for item in [*missing_points, *risks, *findings]:
        cleaned = _normalize_output_item(item)
        if cleaned:
            candidate_issues.append(cleaned)

    synthesized_actions = []
    seen_actions = set()
    for issue in candidate_issues:
        action = _derive_follow_up_action(issue)
        key = action.lower()
        if key not in seen_actions:
            seen_actions.add(key)
            synthesized_actions.append(f"- {action}")
        if len(synthesized_actions) >= 3:
            break

    body_line = ""
    for raw_line in (body or "").splitlines():
        stripped = raw_line.strip()
        if stripped.endswith(":"):
            continue
        normalized = _normalize_output_item(stripped)
        if normalized:
            body_line = normalized.rstrip(".") + "."
            break
    fallback_sentences = _extract_candidate_sentences(body, limit=3)
    fallback_bullets = _prepare_output_bullets(fallback_sentences, limit=3)

    return {
        "Findings": findings or ([f"- {body_line}"] if body_line else fallback_bullets[:1]) or [_default_section_message("Findings")],
        "Risks": risks or (missing_points[:2] if missing_points else fallback_bullets[:2]) or [_default_section_message("Risks")],
        "Missing / Weak points": missing_points or ([item for item in risks if any(term in item.lower() for term in ("does not", "missing", "unclear", "not specify", "not define", "absent", "silent"))][:2] if risks else []) or [_default_section_message("Missing / Weak points")],
        "Recommended follow-up actions": recommended_actions or synthesized_actions or [_default_section_message("Recommended follow-up actions")],
    }


def _is_residential_lease_only(contract_text: str) -> bool:
    text = (contract_text or "").lower()
    has_residential = "residential" in text
    has_residential_only = any(
        phrase in text
        for phrase in ("residential use only", "for residential purposes only", "solely for residential use")
    )
    has_commercial_only = "commercial use only" in text or "commercial purposes only" in text
    return (has_residential and has_residential_only) and not has_commercial_only


def _infer_effective_contract_type(contract_text: str, requested_contract_type: str) -> str:
    explicit = (requested_contract_type or "").strip()
    if explicit and explicit.lower() != "auto-detect":
        return explicit
    text = (contract_text or "").lower()
    score_map = {
        "Lease": (
            ("tenant", 2),
            ("landlord", 2),
            ("lease", 2),
            ("premises", 2),
            ("rent", 2),
            ("security deposit", 2),
            ("lessee", 1),
            ("lessor", 1),
        ),
        "NDA": (
            ("confidential information", 2),
            ("disclosing party", 2),
            ("receiving party", 2),
            ("non-disclosure", 2),
            ("proprietary information", 1),
            ("unauthorized disclosure", 1),
        ),
        "Employment": (
            ("employee", 2),
            ("employer", 2),
            ("salary", 2),
            ("termination of employment", 2),
            ("probation", 2),
            ("notice period", 1),
            ("cost to company", 1),
            ("remuneration", 1),
        ),
        "MSA": (
            ("statement of work", 2),
            ("services", 1),
            ("service provider", 2),
            ("master services", 2),
            ("service levels", 1),
            ("deliverables", 1),
            ("change request", 1),
            ("customer", 1),
        ),
    }
    scores = {}
    for contract_name, weighted_terms in score_map.items():
        score = 0
        for term, weight in weighted_terms:
            if term in text:
                score += weight
        scores[contract_name] = score
    best_name = max(scores, key=scores.get)
    best_score = scores[best_name]
    sorted_scores = sorted(scores.values(), reverse=True)
    runner_up = sorted_scores[1] if len(sorted_scores) > 1 else 0
    if best_score >= 2 and best_score > runner_up:
        return best_name
    return "Auto-detect"


def _lease_clause_presence(contract_text: str) -> dict:
    text = (contract_text or "").lower()
    return {
        "utilities": bool(re.search(r"\b(utilities|utility bills?|electricity|water bill)\b", text)),
        "maintenance": bool(re.search(r"\b(maintain|maintenance|repair|good condition|clean condition|garbage)\b", text)),
        "lease_term": bool(re.search(r"\b(commencing on|period of|term of|expires on|expiry)\b", text)),
        "permitted_use": bool(re.search(r"\b(residential use only|residential purposes only|solely for residential use)\b", text)),
        "notice_period": bool(re.search(r"\b(30 days notice|notice period|written notice)\b", text)),
    }


def _filter_lease_missing_lines(lines, contract_text: str):
    presence = _lease_clause_presence(contract_text)
    filtered = []
    for raw in lines:
        line = (raw or "").strip()
        lowered = line.lower()
        if any(term in lowered for term in ("service level", "sla", "data privacy", "privacy term")):
            continue
        if presence["utilities"] and any(term in lowered for term in ("utilities", "utility")):
            continue
        if presence["maintenance"] and any(term in lowered for term in ("maintenance", "maintain", "repair", "good condition")):
            continue
        if presence["lease_term"] and any(term in lowered for term in ("lease term", "term not", "term missing", "lease period")):
            continue
        if presence["permitted_use"] and any(term in lowered for term in ("permitted use", "residential use", "use restriction")):
            continue
        if presence["notice_period"] and any(term in lowered for term in ("notice period", "30 days notice", "written notice")):
            continue
        filtered.append(raw)
    return filtered


def _finalize_output_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return value
    lines = value.splitlines()
    while lines:
        stripped = lines[-1].strip()
        if not stripped:
            lines.pop()
            continue
        if stripped.startswith("-") and _is_incomplete_bullet(stripped.lstrip("- ").strip()):
            lines.pop()
            continue
        if (
            not stripped.endswith(":")
            and not stripped.lower().startswith("risk score")
            and not stripped.startswith("-")
            and _is_incomplete_bullet(stripped)
        ):
            lines.pop()
            continue
        break
    return "\n".join(lines).strip()


def _postprocess_structured_output(text: str, contract_type: str, contract_text: str) -> str:
    value = (text or "").strip()
    if not value or "lease" not in (contract_type or "").lower():
        return value

    lines = value.splitlines()
    filtered_lines = []
    current_section = ""
    for raw in lines:
        line = raw.strip()
        lowered = line.rstrip(":").lower()
        if lowered in ("key clauses", "risks", "missing / weak", "plain summary"):
            current_section = lowered
            filtered_lines.append(raw)
            continue
        if current_section == "missing / weak":
            pending = _filter_lease_missing_lines([raw], contract_text)
            if not pending:
                continue
        filtered_lines.append(raw)

    result = "\n".join(filtered_lines)
    result = re.sub(
        r"(Missing / Weak:\s*)(\n\s*\n|\nRisk Score:)",
        r"\1\n- No clearly missing or weak clause was identified from the available analysis text.\n\nRisk Score:",
        result,
        flags=re.IGNORECASE,
    )
    if _is_residential_lease_only(contract_text):
        result = re.sub(
            r"residential\s*/\s*commercial lease",
            "residential lease",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            r"residential-commercial lease",
            "residential lease",
            result,
            flags=re.IGNORECASE,
        )
        result = re.sub(
            r"residential/commercial lease agreement",
            "residential lease agreement",
            result,
            flags=re.IGNORECASE,
        )
    result_lines = []
    for raw in result.splitlines():
        stripped = raw.strip()
        if stripped.startswith("-") and _is_incomplete_bullet(stripped.lstrip("- ").strip()):
            continue
        result_lines.append(raw)
    result = "\n".join(result_lines)
    return _finalize_output_text(result)


def _postprocess_agent_output(text: str, contract_type: str, contract_text: str) -> str:
    value = (text or "").strip()
    if not value or "lease" not in (contract_type or "").lower():
        return value
    lines = value.splitlines()
    filtered_lines = []
    current_section = ""
    for raw in lines:
        line = raw.strip()
        lowered = line.rstrip(":").lower()
        if lowered in ("findings", "risks", "missing / weak points", "recommended follow-up actions"):
            current_section = lowered
            filtered_lines.append(raw)
            continue
        if current_section == "missing / weak points":
            pending = _filter_lease_missing_lines([raw], contract_text)
            if not pending:
                continue
        filtered_lines.append(raw)
    result = "\n".join(filtered_lines)
    result = re.sub(
        r"(Missing / Weak points:\s*)(\n\s*\n|\nRecommended follow-up actions:)",
        r"\1\n- No clearly missing or weak role-specific point was identified from the available analysis text.\n\nRecommended follow-up actions:",
        result,
        flags=re.IGNORECASE,
    )
    return _finalize_output_text(result)




# Analyze one contract end-to-end so the UI gets either final text or structured outputs.
def analyze_contract(
    pages,
    fast_mode: bool = False,
    summary_length: str = "Short",
    risk_sensitivity: str = "Balanced",
    contract_type: str = "Auto-detect",
    output_format: str = "Bullets + summary",
    language: str = "English",
    progress_callback: Optional[Callable[[str], None]] = None,
    return_agent_outputs: bool = False,
):
    # Emit stage updates through the callback so progress UI stays in sync.
    def _emit(stage: str):
        if progress_callback:
            progress_callback(stage)

    def _agent_error_fallback(role_name: str, err: Exception) -> str:
        return (
            "Findings:\n"
            "- Not generated due to temporary model throttling.\n"
            "Risks:\n"
            "- Domain analysis may be incomplete for this run.\n"
            "Missing / Weak points:\n"
            f"- Agent call failed for {role_name}: {str(err)[:120]}.\n"
            "Recommended follow-up actions:\n"
            "- Retry in a few seconds or lower worker concurrency."
        )

    def _clause_error_fallback(role_name: str, err: Exception) -> str:
        return (
            "Key Clauses:\n"
            f"- Clause extraction for {role_name} was interrupted by temporary model throttling.\n"
            "Missing / Weak:\n"
            f"- Clause extraction failed for {role_name}: {str(err)[:120]}.\n"
            "- Retry in a few seconds or lower worker concurrency."
        )

    # Validate section completeness to detect truncated model output and trigger retries.
    def _is_complete_output(text: str) -> bool:
        if not text:
            return False
        required_markers = [
            "Key Clauses",
            "Risks",
            "Missing / Weak",
            "Plain Summary",
            "Risk Score:",
        ]
        if not all(marker in text for marker in required_markers):
            return False
        stripped = text.strip()
        # Common truncation endings from token cutoff.
        bad_suffixes = ("...", "**", "-", "•", "Ter.....", "Ter...")
        return not stripped.endswith(bad_suffixes)

    # Detect likely cut-off agent output so we can retry once with a higher cap.
    def _is_likely_truncated_agent_output(text: str) -> bool:
        if not text:
            return True
        stripped = text.strip()
        bad_suffixes = ("...", "**", "-", "â€¢", ":", ";", ",", "Ter.....", "Ter...")
        if stripped.endswith(bad_suffixes):
            return True
        expected_markers = ("Findings", "Risks", "Missing / Weak", "Recommended follow-up actions")
        marker_hits = sum(1 for marker in expected_markers if marker.lower() in stripped.lower())
        if marker_hits < 3:
            return True
        non_empty_lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if not non_empty_lines:
            return True
        last_line = non_empty_lines[-1]
        if last_line.rstrip(":").lower() in {marker.lower() for marker in expected_markers}:
            return True
        return _is_incomplete_bullet(last_line.lstrip("-").strip())

    def _coerce_agent_output(text: str) -> str:
        body = (text or "").strip()
        if not body:
            body = ""
        normalized = body.replace("###", "").replace("**", "")
        aliases = {
            "findings": "Findings",
            "key clauses": "Findings",
            "risks": "Risks",
            "missing / weak points": "Missing / Weak points",
            "missing / weak": "Missing / Weak points",
            "recommended follow-up actions": "Recommended follow-up actions",
            "recommended actions": "Recommended follow-up actions",
        }
        sections = {
            "Findings": [],
            "Risks": [],
            "Missing / Weak points": [],
            "Recommended follow-up actions": [],
        }
        current = None
        for raw in normalized.splitlines():
            line = raw.strip()
            if not line:
                continue
            header = re.sub(r"^\d+\)\s*", "", line.rstrip(":").strip().lower())
            mapped = aliases.get(header)
            if mapped:
                current = mapped
                continue
            if current:
                sections[current].append(line)
        if not any(sections.values()):
            sections["Findings"] = [body]
        fallback_sections = _build_agent_section_fallbacks(sections, body)

        def _fmt(section_name: str):
            items = sections[section_name] or fallback_sections.get(section_name, [])
            cleaned = _prepare_output_bullets(items, limit=4)
            if cleaned:
                return cleaned
            return fallback_sections.get(section_name, [_default_section_message(section_name)])

        lines = [
            "Findings:",
            *_fmt("Findings"),
            "Risks:",
            *_fmt("Risks"),
            "Missing / Weak points:",
            *_fmt("Missing / Weak points"),
            "Recommended follow-up actions:",
            *_fmt("Recommended follow-up actions"),
        ]
        return "\n".join(lines).strip()

    # Ensure final output always has all required sections even when model text is malformed.
    def _coerce_structured_output(text: str) -> str:
        body = (text or "").strip()
        if not body:
            body = ""

        normalized = body.replace("###", "").replace("**", "")
        aliases = {
            "findings": "Key Clauses",
            "key clauses": "Key Clauses",
            "risks": "Risks",
            "missing / weak": "Missing / Weak",
            "missing/weak": "Missing / Weak",
            "missing / weak points": "Missing / Weak",
            "plain summary": "Plain Summary",
            "recommended actions": "Plain Summary",
            "recommended follow-up actions": "Plain Summary",
        }
        sections = {
            "Key Clauses": [],
            "Risks": [],
            "Missing / Weak": [],
            "Plain Summary": [],
        }
        risk_score = "Risk Score: Medium"
        current = None
        for raw in normalized.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.lower().startswith("risk score"):
                risk_score = line if ":" in line else f"Risk Score: {line.split()[-1]}"
                current = None
                continue
            header = re.sub(r"^\d+\)\s*", "", line.rstrip(":").strip().lower())
            mapped = aliases.get(header)
            if mapped:
                current = mapped
                continue
            if current:
                sections[current].append(line)

        fallback_sentences = _extract_candidate_sentences(body, limit=8)
        if not any(sections.values()):
            sections["Key Clauses"] = fallback_sentences[:4]
            sections["Risks"] = [
                sentence for sentence in fallback_sentences
                if any(term in sentence.lower() for term in ("risk", "liability", "terminate", "termination", "breach", "penalty", "indemn", "unclear"))
            ][:3]
            sections["Plain Summary"] = [" ".join(fallback_sentences[:3])] if fallback_sentences else [body]

        def _auto_plain_summary() -> str:
            key = _normalize_output_item(sections["Key Clauses"][0]) if sections["Key Clauses"] else ""
            risk = _normalize_output_item(sections["Risks"][0]) if sections["Risks"] else ""
            if key and risk:
                return f"{key} Also, {risk}"
            if key:
                return key
            if risk:
                return f"Primary concern: {risk}"
            return "Summary generated from available findings is limited."

        inferred_missing = [
            sentence for sentence in fallback_sentences
            if any(term in sentence.lower() for term in ("missing", "unclear", "not specify", "not defined", "not define", "absent", "silent", "weak"))
        ]

        def _fmt(section_name: str):
            items = _prepare_output_bullets(sections[section_name], limit=4)
            if not items:
                if section_name == "Plain Summary":
                    return [_auto_plain_summary()]
                if section_name == "Key Clauses":
                    items = _prepare_output_bullets(fallback_sentences, limit=6)
                elif section_name == "Risks":
                    items = _prepare_output_bullets(sections["Missing / Weak"] or inferred_missing, limit=5)
                elif section_name == "Missing / Weak":
                    items = _prepare_output_bullets(inferred_missing, limit=4)
            if not items:
                return [_default_section_message(section_name)]
            if section_name == "Plain Summary":
                summary_source = sections["Plain Summary"] or fallback_sentences[:2]
                summary = " ".join(_normalize_output_item(item) for item in summary_source if _normalize_output_item(item))[:400]
                return [summary or _auto_plain_summary()]
            section_limits = {"Key Clauses": 6, "Risks": 5, "Missing / Weak": 4}
            return items[: section_limits.get(section_name, 4)]

        lines = [
            "Key Clauses:",
            *_fmt("Key Clauses"),
            "",
            "Risks:",
            *_fmt("Risks"),
            "",
            "Missing / Weak:",
            *_fmt("Missing / Weak"),
            "",
            "Plain Summary:",
            *_fmt("Plain Summary"),
            "",
            risk_score,
        ]
        return "\n".join(lines).strip()


    def _clip(text: str, max_chars: int) -> str:
        value = (text or "").strip()
        if len(value) <= max_chars:
            return value
        return value[:max_chars].rstrip() + "..."

    # Normalize per-agent output so each tab remains complete and readable.
    def _coerce_agent_output(text: str) -> str:
        body = (text or "").strip()
        if not body:
            body = ""
        normalized = body.replace("###", "").replace("**", "")
        aliases = {
            "findings": "Findings",
            "key clauses": "Findings",
            "risks": "Risks",
            "missing / weak points": "Missing / Weak points",
            "missing / weak": "Missing / Weak points",
            "recommended follow-up actions": "Recommended follow-up actions",
            "recommended actions": "Recommended follow-up actions",
        }
        sections = {
            "Findings": [],
            "Risks": [],
            "Missing / Weak points": [],
            "Recommended follow-up actions": [],
        }
        current = None
        for raw in normalized.splitlines():
            line = raw.strip()
            if not line:
                continue
            header = re.sub(r"^\d+\)\s*", "", line.rstrip(":").strip().lower())
            mapped = aliases.get(header)
            if mapped:
                current = mapped
                continue
            if current:
                sections[current].append(line)
        fallback_sentences = _extract_candidate_sentences(body, limit=8)
        if not any(sections.values()):
            sections["Findings"] = fallback_sentences[:4] or [body]
            sections["Risks"] = [
                sentence for sentence in fallback_sentences
                if any(term in sentence.lower() for term in ("risk", "liability", "terminate", "termination", "breach", "penalty", "indemn", "unclear"))
            ][:3]
        fallback_sections = _build_agent_section_fallbacks(sections, body)

        def _fmt(section_name: str):
            items = sections[section_name] or fallback_sections.get(section_name, [])
            section_limits = {
                "Findings": 6,
                "Risks": 5,
                "Missing / Weak points": 4,
                "Recommended follow-up actions": 4,
            }
            cleaned = _prepare_output_bullets(items, limit=section_limits.get(section_name, 4))
            if cleaned:
                return cleaned
            return fallback_sections.get(section_name, [_default_section_message(section_name)])

        lines = [
            "Findings:",
            *_fmt("Findings"),
            "Risks:",
            *_fmt("Risks"),
            "Missing / Weak points:",
            *_fmt("Missing / Weak points"),
            "Recommended follow-up actions:",
            *_fmt("Recommended follow-up actions"),
        ]
        return "\n".join(lines).strip()

    def _agent_num_predict() -> int:
        # Higher default to reduce truncation in role tabs.
        return _env_int("CLAUSEAI_AGENT_NUM_PREDICT", 500, minimum=400)

    contract_text = parse_contract_text(pages)
    prepared_inputs = _prepare_contract_inputs(contract_text)
    contract_text_for_model = prepared_inputs["contract_text_for_model"]
    contract_text_for_agents = prepared_inputs["contract_text_for_agents"]
    max_index_chunks = min(3, _env_int("CLAUSEAI_MAX_INDEX_CHUNKS", 3))
    deep_mode = False
    turbo_mode = os.getenv("CLAUSEAI_TURBO_MODE", "1") == "1"
    doc_id = prepared_inputs["doc_id"]
    effective_contract_type = _infer_effective_contract_type(contract_text, contract_type)
    evidence_signals = prepared_inputs["evidence_signals"]
    validated_extraction_cache = {"value": None}

    # Resolve validated extraction lazily so unused branches avoid an extra LLM call.
    def _get_validated_extraction() -> str:
        cached_value = validated_extraction_cache["value"]
        if cached_value is None:
            cached_value = _extract_validated_key_fields(contract_text_for_model, doc_id)
            validated_extraction_cache["value"] = cached_value
        return cached_value

    role_signature_map = {
        role_name: _hash_text(role.title + role.mission + "||".join(role.checks))
        for role_name, role in ANALYST_ROLES.items()
    }
    clause_signature_map = {
        role_name: _hash_text(role.title + "||".join(role.checks))
        for role_name, role in ANALYST_ROLES.items()
    }

    def _ensure_contract_indexed() -> bool:
        marker_key = _cache_key(
            doc_id,
            "contract_chunks",
            chunk_size=2500,
            chunk_overlap=300,
            max_chunks=max_index_chunks,
        )
        already_indexed = retrieve_analysis_artifact(marker_key)
        if already_indexed:
            return True

        indexed = index_contract_chunks(list(prepared_inputs["index_chunks"][:max_index_chunks]), doc_id=doc_id)
        if indexed:
            store_analysis_artifact(marker_key, {"indexed": True})
        return indexed

    # Estimate token budget from verbosity settings to reduce truncation while staying fast.
    def _final_num_predict(
        summary_len: str,
        output_fmt: str,
        deep: bool = False,
        text_chars: int = 0,
    ) -> int:
        base = {"Short": 600, "Medium": 600, "Detailed": 600}.get(summary_len, 600)
        if deep:
            base += 45
        return max(500, base)

    agent_plan = build_agent_execution_plan(
        available_roles=ANALYST_ROLES,
        contract_text=contract_text,
        contract_type=effective_contract_type,
        risk_sensitivity=risk_sensitivity,
        use_local_llm=USE_LOCAL_LLM,
        configured_workers=os.getenv("CLAUSEAI_AGENT_WORKERS", ""),
    )
    ordered_roles = agent_plan.ordered_roles

    # Execute all specialist agents and collect outputs for optional downstream synthesis.
    def _collect_agent_outputs(
        text_for_agents: str,
        use_retrieval_local: bool,
        doc_id_local: Optional[str],
        emit_progress: bool,
    ):
        role_names_to_run = list(ordered_roles)

        # Run a single role with optional retrieval context to ground specialist reasoning.
        def _run_single_role(role_name: str):
            role = ANALYST_ROLES[role_name]
            validated_extraction = _get_validated_extraction()
            role_cache_key = _cache_key(
                doc_id_local or doc_id,
                "agent_role",
                role=role_name,
                format_ver=AGENT_OUTPUT_FORMAT_VERSION,
                role_sig=role_signature_map[role_name],
                retrieval=int(bool(use_retrieval_local)),
                text_sig=_hash_text(text_for_agents),
                contract_type=effective_contract_type,
                evidence_sig=_hash_text(evidence_signals),
                extraction_sig=_hash_text(validated_extraction),
            )
            cached_role_output = retrieve_analysis_artifact(role_cache_key)
            if isinstance(cached_role_output, str) and cached_role_output.strip():
                return role_name, cached_role_output

            role_context = ""
            if use_retrieval_local:
                retrieval_query = f"{role_name} risk analysis for contract obligations"
                role_context = retrieve_context(retrieval_query, doc_id=doc_id_local, k=1)
            base_predict = _agent_num_predict()
            retry_steps = (0,)
            role_output = ""
            for bump in retry_steps:
                role_output = run_role_agent(
                    role_name,
                    text_for_agents,
                    retrieved_context=role_context,
                    num_predict=base_predict + bump,
                    contract_type=effective_contract_type,
                    evidence_signals=evidence_signals,
                    validated_extraction=validated_extraction,
                )
                if not _is_likely_truncated_agent_output(role_output):
                    break
            normalized_output = _coerce_agent_output(role_output)
            normalized_output = _postprocess_agent_output(normalized_output, effective_contract_type, contract_text)
            store_analysis_artifact(role_cache_key, normalized_output)
            return role_name, normalized_output

        role_output_map = {}
        emitted_stage_names = set()
        inter_agent_delay = float(os.getenv("CLAUSEAI_INTER_AGENT_DELAY", "2.0"))

        for role_idx, role_name in enumerate(role_names_to_run):
            if role_idx > 0 and inter_agent_delay > 0:
                time.sleep(inter_agent_delay)

            try:
                role_name, role_output = _run_single_role(role_name)
            except Exception as err:
                role_output = _agent_error_fallback(role_name, err)
            role_output_map[role_name] = role_output

            if emit_progress:
                stage_name = agent_plan.stage_by_role.get(role_name)
                if stage_name and stage_name not in emitted_stage_names:
                    _emit(stage_name)
                    emitted_stage_names.add(stage_name)

        if emit_progress:
            for stage_name in agent_plan.ordered_stages:
                if stage_name not in emitted_stage_names:
                    _emit(stage_name)

        return role_output_map

    # Run additional collaboration rounds where each specialist can refine output using peer notes.
    def _run_multi_turn_agent_interaction(
        role_output_map,
        text_for_agents: str,
        use_retrieval_local: bool,
        doc_id_local: Optional[str],
    ):
        if len(ordered_roles) < 2:
            return role_output_map

        enabled = os.getenv("CLAUSEAI_ENABLE_MULTI_TURN_AGENT_INTERACTION", "1") == "1"
        max_turns = _env_int("CLAUSEAI_AGENT_INTERACTION_TURNS", 2, minimum=1)
        if not enabled or max_turns <= 1:
            return role_output_map

        inter_agent_delay = float(os.getenv("CLAUSEAI_INTER_AGENT_DELAY", "2.0"))

        def _refine_turn(current_map, turn_idx: int):
            next_map = dict(current_map)

            def _run_single_role_refinement(role_name: str):
                validated_extraction = _get_validated_extraction()
                role_context = ""
                if use_retrieval_local:
                    retrieval_query = f"{role_name} risk analysis for contract obligations"
                    role_context = retrieve_context(retrieval_query, doc_id=doc_id_local, k=1)

                peer_notes = []
                for peer_role in ordered_roles:
                    if peer_role == role_name:
                        continue
                    peer_output = current_map.get(peer_role, "")
                    if peer_output:
                        peer_notes.append(f"{peer_role.title()}:\n{_clip(peer_output, 360)}")
                peer_context = "\n\n".join(peer_notes) if peer_notes else ""
                role = ANALYST_ROLES[role_name]
                role_cache_key = _cache_key(
                    doc_id_local or doc_id,
                    "agent_role_refine",
                    role=role_name,
                    turn=turn_idx,
                    max_turns=max_turns,
                    format_ver=AGENT_OUTPUT_FORMAT_VERSION,
                    role_sig=role_signature_map[role_name],
                    retrieval=int(bool(use_retrieval_local)),
                    text_sig=_hash_text(text_for_agents),
                    peer_sig=_hash_text(peer_context),
                    contract_type=effective_contract_type,
                    evidence_sig=_hash_text(evidence_signals),
                    extraction_sig=_hash_text(validated_extraction),
                )
                cached_role_output = retrieve_analysis_artifact(role_cache_key)
                if isinstance(cached_role_output, str) and cached_role_output.strip():
                    return role_name, cached_role_output

                base_predict = _agent_num_predict()
                retry_steps = (0,)
                refined_output = ""
                for bump in retry_steps:
                    refined_output = run_role_agent(
                        role_name,
                        text_for_agents,
                        retrieved_context=role_context,
                        num_predict=base_predict + bump,
                        peer_context=peer_context,
                        turn_number=turn_idx,
                        max_turns=max_turns,
                        contract_type=effective_contract_type,
                        evidence_signals=evidence_signals,
                        validated_extraction=validated_extraction,
                    )
                    if not _is_likely_truncated_agent_output(refined_output):
                        break
                normalized_output = _coerce_agent_output(refined_output)
                normalized_output = _postprocess_agent_output(normalized_output, effective_contract_type, contract_text)
                store_analysis_artifact(role_cache_key, normalized_output)
                return role_name, normalized_output

            for role_name in ordered_roles:
                time.sleep(inter_agent_delay)
                try:
                    role_name, role_output = _run_single_role_refinement(role_name)
                except Exception as err:
                    role_output = _agent_error_fallback(role_name, err)
                next_map[role_name] = role_output
            return next_map

        use_langgraph = os.getenv("CLAUSEAI_USE_LANGGRAPH", "1") == "1"
        if use_langgraph:
            try:
                from langgraph.graph import END, START, StateGraph

                def _refine_round_node(state):
                    current_map = state["current_map"]
                    turn_idx = int(state["turn_idx"])
                    next_map = _refine_turn(current_map, turn_idx=turn_idx)
                    return {"current_map": next_map, "turn_idx": turn_idx + 1}

                def _route_next(state):
                    return "refine_round" if int(state["turn_idx"]) <= max_turns else "end"

                graph_builder = StateGraph(dict)
                graph_builder.add_node("refine_round", _refine_round_node)
                graph_builder.add_edge(START, "refine_round")
                graph_builder.add_conditional_edges(
                    "refine_round",
                    _route_next,
                    {"refine_round": "refine_round", "end": END},
                )
                graph = graph_builder.compile()
                final_state = graph.invoke({"current_map": dict(role_output_map), "turn_idx": 2})
                return final_state.get("current_map", role_output_map)
            except Exception:
                pass

        current_map = dict(role_output_map)
        for turn_idx in range(2, max_turns + 1):
            current_map = _refine_turn(current_map, turn_idx=turn_idx)
        return current_map

    # Extract domain-specific clauses in parallel so synthesis has grounded clause evidence.
    def _collect_domain_clause_outputs(
        text_for_model: str,
        use_retrieval_local: bool,
        doc_id_local: Optional[str],
    ):
        role_names_to_run = list(ordered_roles)

        def _run_single_clause_extractor(role_name: str):
            role = ANALYST_ROLES[role_name]
            checks = "\n".join(f"- {item}" for item in role.checks)
            validated_extraction = _get_validated_extraction()
            clause_cache_key = _cache_key(
                doc_id_local or doc_id,
                "domain_clause",
                role=role_name,
                role_sig=clause_signature_map[role_name],
                retrieval=int(bool(use_retrieval_local)),
                text_sig=_hash_text(text_for_model),
                contract_type=effective_contract_type,
                evidence_sig=_hash_text(evidence_signals),
                extraction_sig=_hash_text(validated_extraction),
            )
            cached_clause_output = retrieve_analysis_artifact(clause_cache_key)
            if isinstance(cached_clause_output, str) and cached_clause_output.strip():
                return role_name, cached_clause_output
            role_context = ""
            if use_retrieval_local:
                retrieval_query = f"{role_name} key clause extraction from contract"
                role_context = retrieve_context(retrieval_query, doc_id=doc_id_local, k=2)
            prompt = build_clause_extraction_prompt(
                role_title=role.title,
                checks=checks,
                contract_text=text_for_model,
                retrieved_context=role_context,
                contract_type=effective_contract_type,
                evidence_signals=evidence_signals,
                validated_extraction=validated_extraction,
            )
            clause_output = get_llm_response(prompt, num_predict=500)
            store_analysis_artifact(clause_cache_key, clause_output)
            return role_name, clause_output

        clause_output_map = {}
        inter_clause_delay = float(os.getenv("CLAUSEAI_INTER_CLAUSE_DELAY", "2.0"))

        for clause_idx, role_name in enumerate(role_names_to_run):
            if clause_idx > 0 and inter_clause_delay > 0:
                time.sleep(inter_clause_delay)

            try:
                role_name, role_output = _run_single_clause_extractor(role_name)
            except Exception as err:
                role_output = _clause_error_fallback(role_name, err)
            clause_output_map[role_name] = role_output
        return clause_output_map

    # Reorder collected role outputs deterministically to keep UI tabs stable.
    def _ordered_agent_output_dict(role_output_map):
        return {role_name: role_output_map[role_name] for role_name in ordered_roles if role_name in role_output_map}

    if fast_mode:
        _emit("Generating embeddings...")
        _emit("Detecting contract type...")
        _emit("Planning agent execution...")
        for stage_name in agent_plan.ordered_stages:
            _emit(stage_name)
        _emit("Aggregating responses...")
        prompt = build_fast_summary_prompt(contract_text_for_model)
        fast_cache_key = _cache_key(
            doc_id,
            "fast_summary",
            text_sig=_hash_text(contract_text_for_model),
        )
        cached_result = retrieve_analysis_artifact(fast_cache_key)
        if isinstance(cached_result, str) and cached_result.strip():
            _emit("Finalizing results...")
            return cached_result
        _emit("Finalizing results...")
        result = get_llm_response(prompt, num_predict=600)
        store_analysis_artifact(fast_cache_key, result)
        return result

    if turbo_mode:
        _emit("Generating embeddings...")
        use_retrieval = vectorstore_available()
        retrieved_context = ""
        validated_future = None
        with ThreadPoolExecutor(max_workers=2) as prework_executor:
            validated_future = prework_executor.submit(_get_validated_extraction)
            if use_retrieval:
                use_retrieval = _ensure_contract_indexed()
                if use_retrieval:
                    retrieved_context = retrieve_context(
                        "key obligations payment termination liability confidentiality governing law indemnity",
                        doc_id=doc_id,
                        k=2,
                    )
            validated_extraction = validated_future.result()
        _emit("Detecting contract type...")
        _emit("Planning agent execution...")

        length_rule = {
            "Short": "Total output <= 600 words.",
            "Medium": "Total output <= 600 words.",
            "Detailed": "Total output <= 600 words.",
        }.get(summary_length, "Total output <= 600 words.")

        risk_rule = {
            "Conservative": "Flag more risks and ambiguities, even if minor.",
            "Balanced": "Flag meaningful risks and ambiguities only.",
            "Aggressive": "Only flag high-confidence, material risks.",
        }.get(risk_sensitivity, "Flag meaningful risks and ambiguities only.")

        contract_hint = (
            "If not clear, say 'Contract type unclear'."
            if effective_contract_type == "Auto-detect"
            else f"Focus on {effective_contract_type} contract patterns."
        )

        if output_format == "Summary only":
            format_rule = "Provide summary only. Do not include bullets."
        elif output_format == "Bullets only":
            format_rule = "Provide bullets only. Do not include a summary section."
        else:
            format_rule = "Include both bullets and summary."

        language_rule = (
            "Use simple, plain English."
            if language == "Simple English"
            else "Use clear professional English."
        )

        final_prompt = build_turbo_analysis_prompt(
            contract_text=contract_text_for_model,
            extracted_signals=evidence_signals,
            retrieved_context=retrieved_context,
            length_rule=length_rule,
            risk_rule=risk_rule,
            contract_hint=contract_hint,
            format_rule=format_rule,
            language_rule=language_rule,
            contract_type=effective_contract_type,
            validated_extraction=validated_extraction,
        )
        final_cache_key = _cache_key(
            doc_id,
            "final_turbo",
            summary_length=summary_length,
            risk_sensitivity=risk_sensitivity,
            contract_type=effective_contract_type,
            output_format=output_format,
            language=language,
            text_sig=_hash_text(contract_text_for_model),
            rules_sig=_hash_text(evidence_signals),
            retrieval_sig=_hash_text(retrieved_context),
            extraction_sig=_hash_text(validated_extraction),
        )

        role_output_future = None
        if return_agent_outputs:
            with ThreadPoolExecutor(max_workers=2) as executor:
                role_output_future = executor.submit(
                    _collect_agent_outputs,
                    contract_text_for_agents,
                    use_retrieval_local=use_retrieval,
                    doc_id_local=doc_id,
                    emit_progress=False,
                )
                cached_result = retrieve_analysis_artifact(final_cache_key)
                if isinstance(cached_result, str) and cached_result.strip():
                    _emit("Aggregating responses...")
                    _emit("Finalizing results...")
                    result = cached_result
                else:
                    _emit("Aggregating responses...")
                    _emit("Finalizing results...")
                    result = get_llm_response(
                        final_prompt,
                        num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)),
                    )
                    if output_format != "Summary only":
                        result = _coerce_structured_output(result)
                        result = _postprocess_structured_output(result, effective_contract_type, contract_text)
                        result = _finalize_output_text(result)
                    store_analysis_artifact(final_cache_key, result)
                _emit("Running lightweight agent breakdown...")
                role_output_map = role_output_future.result()
            return {
                "final_output": result,
                "agent_outputs": _ordered_agent_output_dict(role_output_map),
            }

        cached_result = retrieve_analysis_artifact(final_cache_key)
        if isinstance(cached_result, str) and cached_result.strip():
            _emit("Aggregating responses...")
            _emit("Finalizing results...")
            result = cached_result
        else:
            _emit("Aggregating responses...")
            _emit("Finalizing results...")
            result = get_llm_response(
                final_prompt,
                num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)),
            )
            if output_format != "Summary only":
                result = _coerce_structured_output(result)
                result = _postprocess_structured_output(result, effective_contract_type, contract_text)
                result = _finalize_output_text(result)
            store_analysis_artifact(final_cache_key, result)
        return result

    # Deep analysis is the default path so retrieval + multi-agent synthesis runs by default.
    # Set CLAUSEAI_DEEP_ANALYSIS=0 only if you explicitly want the ultra-fast single-call path.
    if not deep_mode:
        _emit("Generating embeddings...")
        _emit("Detecting contract type...")
        _emit("Planning agent execution...")
        for stage_name in agent_plan.ordered_stages:
            _emit(stage_name)
        validated_extraction = _get_validated_extraction()

        length_rule = {
            "Short": "Total output <= 600 words.",
            "Medium": "Total output <= 600 words.",
            "Detailed": "Total output <= 600 words.",
        }.get(summary_length, "Total output <= 600 words.")

        risk_rule = {
            "Conservative": "Flag more risks and ambiguities, even if minor.",
            "Balanced": "Flag meaningful risks and ambiguities only.",
            "Aggressive": "Only flag high-confidence, material risks.",
        }.get(risk_sensitivity, "Flag meaningful risks and ambiguities only.")

        contract_hint = (
            "If not clear, say 'Contract type unclear'."
            if effective_contract_type == "Auto-detect"
            else f"Focus on {effective_contract_type} contract patterns."
        )

        if output_format == "Summary only":
            format_rule = "Provide summary only. Do not include bullets."
        elif output_format == "Bullets only":
            format_rule = "Provide bullets only. Do not include a summary section."
        else:
            format_rule = "Include both bullets and summary."

        language_rule = (
            "Use simple, plain English."
            if language == "Simple English"
            else "Use clear professional English."
        )

        final_prompt = build_direct_analysis_prompt(
            contract_text=contract_text_for_model,
            length_rule=length_rule,
            risk_rule=risk_rule,
            contract_hint=contract_hint,
            format_rule=format_rule,
            language_rule=language_rule,
            contract_type=effective_contract_type,
            evidence_signals=evidence_signals,
            validated_extraction=validated_extraction,
        )
        final_cache_key = _cache_key(
            doc_id,
            "final_direct",
            summary_length=summary_length,
            risk_sensitivity=risk_sensitivity,
            contract_type=effective_contract_type,
            output_format=output_format,
            language=language,
            text_sig=_hash_text(contract_text_for_model),
            extraction_sig=_hash_text(validated_extraction),
        )

        if return_agent_outputs:
            with ThreadPoolExecutor(max_workers=2) as executor:
                agent_breakdown_future = executor.submit(
                    lambda: _run_multi_turn_agent_interaction(
                        _collect_agent_outputs(
                            contract_text_for_agents,
                            use_retrieval_local=False,
                            doc_id_local=None,
                            emit_progress=False,
                        ),
                        contract_text_for_agents,
                        use_retrieval_local=False,
                        doc_id_local=None,
                    )
                )
                cached_result = retrieve_analysis_artifact(final_cache_key)
                if isinstance(cached_result, str) and cached_result.strip():
                    _emit("Aggregating responses...")
                    _emit("Finalizing results...")
                    result = cached_result
                else:
                    _emit("Aggregating responses...")
                    _emit("Finalizing results...")
                    result = get_llm_response(
                        final_prompt,
                        num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)),
                    )
                    if output_format != "Summary only":
                        result = _coerce_structured_output(result)
                        result = _postprocess_structured_output(result, effective_contract_type, contract_text)
                        result = _finalize_output_text(result)
                    store_analysis_artifact(final_cache_key, result)
                role_output_map = agent_breakdown_future.result()
            return {
                "final_output": result,
                "agent_outputs": _ordered_agent_output_dict(role_output_map),
            }
        cached_result = retrieve_analysis_artifact(final_cache_key)
        if isinstance(cached_result, str) and cached_result.strip():
            _emit("Aggregating responses...")
            _emit("Finalizing results...")
            result = cached_result
        else:
            _emit("Aggregating responses...")
            _emit("Finalizing results...")
            result = get_llm_response(
                final_prompt,
                num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)),
            )
            if output_format != "Summary only":
                result = _coerce_structured_output(result)
                result = _postprocess_structured_output(result, effective_contract_type, contract_text)
                result = _finalize_output_text(result)
            store_analysis_artifact(final_cache_key, result)
        return result

    use_retrieval = vectorstore_available()
    with ThreadPoolExecutor(max_workers=2) as prework_executor:
        validated_future = prework_executor.submit(_get_validated_extraction)
        if use_retrieval:
            _emit("Generating embeddings...")
            use_retrieval = _ensure_contract_indexed()
        else:
            _emit("Generating embeddings...")
        validated_extraction = validated_future.result()
    _emit("Detecting contract type...")
    _emit("Extracting domain clauses...")
    enable_clause_extraction = os.getenv("CLAUSEAI_ENABLE_PARALLEL_CLAUSE_EXTRACTION", "1") == "1"
    clause_output_map = {}
    if enable_clause_extraction:
        clause_output_map = _collect_domain_clause_outputs(
            contract_text_for_model,
            use_retrieval_local=use_retrieval,
            doc_id_local=doc_id,
        )
    _emit("Planning agent execution...")

    role_outputs = []
    role_output_map = _collect_agent_outputs(
        contract_text_for_agents,
        use_retrieval_local=use_retrieval,
        doc_id_local=doc_id,
        emit_progress=True,
    )
    role_output_map = _run_multi_turn_agent_interaction(
        role_output_map,
        contract_text_for_agents,
        use_retrieval_local=use_retrieval,
        doc_id_local=doc_id,
    )

    for role_name in ordered_roles:
        role_output = role_output_map.get(role_name)
        if role_output:
            role_outputs.append(f"{role_name.upper()} ANALYST:\n{_clip(role_output, 550)}")

    length_rule = {
        "Short": "Total output <= 140 words.",
        "Medium": "Total output <= 220 words.",
        "Detailed": "Total output <= 320 words.",
    }.get(summary_length, "Total output <= 220 words.")

    risk_rule = {
        "Conservative": "Flag more risks and ambiguities, even if minor.",
        "Balanced": "Flag meaningful risks and ambiguities only.",
        "Aggressive": "Only flag high-confidence, material risks.",
    }.get(risk_sensitivity, "Flag meaningful risks and ambiguities only.")

    contract_hint = (
        "If not clear, say 'Contract type unclear'."
        if effective_contract_type == "Auto-detect"
        else f"Focus on {effective_contract_type} contract patterns."
    )

    if output_format == "Summary only":
        format_rule = "Provide summary only. Do not include bullets."
    elif output_format == "Bullets only":
        format_rule = "Provide bullets only. Do not include a summary section."
    else:
        format_rule = "Include both bullets and summary."

    language_rule = "Use simple, plain English." if language == "Simple English" else "Use clear professional English."

    _emit("Aggregating responses...")
    clause_outputs = []
    for role_name in ordered_roles:
        clause_text = clause_output_map.get(role_name)
        if clause_text:
            clause_outputs.append(f"{role_name.upper()} CLAUSE EXTRACTION:\n{_clip(clause_text, 420)}")

    final_prompt = build_synthesis_prompt(
        contract_text=contract_text,
        clause_extracts=chr(10).join(clause_outputs) if clause_outputs else "No clause extracts were available.",
        analyst_notes=chr(10).join(role_outputs),
        length_rule=length_rule,
        risk_rule=risk_rule,
        contract_hint=contract_hint,
        format_rule=format_rule,
        language_rule=language_rule,
        contract_type=effective_contract_type,
        evidence_signals=evidence_signals,
        validated_extraction=validated_extraction,
    )
    final_cache_key = _cache_key(
        doc_id,
        "final_deep",
        summary_length=summary_length,
        risk_sensitivity=risk_sensitivity,
        contract_type=effective_contract_type,
        output_format=output_format,
        language=language,
        clause_sig=_hash_text("\n".join(clause_outputs)),
        role_sig=_hash_text("\n".join(role_outputs)),
        extraction_sig=_hash_text(validated_extraction),
    )

    _emit("Finalizing results...")
    cached_result = retrieve_analysis_artifact(final_cache_key)
    if isinstance(cached_result, str) and cached_result.strip():
        result = cached_result
    else:
        result = get_llm_response(
            final_prompt,
            num_predict=_final_num_predict(
                summary_length,
                output_format,
                deep=True,
                text_chars=len(contract_text_for_model),
            ),
        )
        if not _is_complete_output(result):
            result = get_llm_response(
                final_prompt,
                num_predict=_final_num_predict(
                    summary_length,
                    output_format,
                    deep=True,
                    text_chars=len(contract_text_for_model),
                ) + 80,
            )
        if output_format != "Summary only":
            result = _coerce_structured_output(result)
            result = _postprocess_structured_output(result, effective_contract_type, contract_text)
            result = _finalize_output_text(result)
        store_analysis_artifact(final_cache_key, result)
    if return_agent_outputs:
        payload = {
            "final_output": result,
            "agent_outputs": _ordered_agent_output_dict(role_output_map),
        }
        if clause_output_map:
            payload["domain_clause_outputs"] = {
                role_name: clause_output_map[role_name]
                for role_name in ordered_roles
                if role_name in clause_output_map
            }
        return payload
    return result


# Run only specialist agents and return per-role outputs for detailed breakdown views.
def analyze_agent_breakdown(
    pages,
    contract_type: str = "Auto-detect",
    progress_callback: Optional[Callable[[str], None]] = None,
):
    # Emit stage updates through the callback so progress UI stays in sync.
    def _emit(stage: str):
        if progress_callback:
            progress_callback(stage)

    contract_text = parse_contract_text(pages)
    prepared_inputs = _prepare_contract_inputs(contract_text)
    contract_text_for_agents = prepared_inputs["contract_text_for_agents"]
    max_index_chunks = min(3, _env_int("CLAUSEAI_MAX_INDEX_CHUNKS", 3))
    doc_id = prepared_inputs["doc_id"]
    effective_contract_type = _infer_effective_contract_type(contract_text, contract_type)
    evidence_signals = prepared_inputs["evidence_signals"]
    validated_extraction = _get_validated_extraction()

    def _agent_error_fallback(role_name: str, err: Exception) -> str:
        return (
            "Findings:\n"
            "- Not generated due to temporary model throttling.\n"
            "Risks:\n"
            "- Domain analysis may be incomplete for this run.\n"
            "Missing / Weak points:\n"
            f"- Agent call failed for {role_name}: {str(err)[:120]}.\n"
            "Recommended follow-up actions:\n"
            "- Retry in a few seconds or lower worker concurrency."
        )

    def _ensure_contract_indexed() -> bool:
        marker_key = _cache_key(
            doc_id,
            "contract_chunks",
            chunk_size=2500,
            chunk_overlap=300,
            max_chunks=max_index_chunks,
        )
        already_indexed = retrieve_analysis_artifact(marker_key)
        if already_indexed:
            return True

        indexed = index_contract_chunks(list(prepared_inputs["index_chunks"][:max_index_chunks]), doc_id=doc_id)
        if indexed:
            store_analysis_artifact(marker_key, {"indexed": True})
        return indexed

    use_retrieval = vectorstore_available()
    if use_retrieval:
        _emit("Generating embeddings...")
        use_retrieval = _ensure_contract_indexed()
    else:
        _emit("Generating embeddings...")
    _emit("Detecting contract type...")
    _emit("Planning agent execution...")

    agent_plan = build_agent_execution_plan(
        available_roles=ANALYST_ROLES,
        contract_text=contract_text,
        contract_type=effective_contract_type,
        risk_sensitivity="Balanced",
        use_local_llm=USE_LOCAL_LLM,
        configured_workers=os.getenv("CLAUSEAI_AGENT_WORKERS", ""),
    )
    ordered_roles = agent_plan.ordered_roles

    # Detect likely cut-off agent output so we can retry once with a higher cap.
    def _is_likely_truncated_agent_output(text: str) -> bool:
        if not text:
            return True
        stripped = text.strip()
        bad_suffixes = ("...", "**", "-", "â€¢", ":", ";", ",", "Ter.....", "Ter...")
        if stripped.endswith(bad_suffixes):
            return True
        expected_markers = ("Findings", "Risks", "Missing / Weak", "Recommended follow-up actions")
        marker_hits = sum(1 for marker in expected_markers if marker.lower() in stripped.lower())
        if marker_hits < 3:
            return True
        non_empty_lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        if not non_empty_lines:
            return True
        last_line = non_empty_lines[-1]
        if last_line.rstrip(":").lower() in {marker.lower() for marker in expected_markers}:
            return True
        return _is_incomplete_bullet(last_line.lstrip("-").strip())

    # Run one specialist role to keep threaded execution logic concise and reusable.
    def _run_single_role(role_name: str):
        role = ANALYST_ROLES[role_name]
        role_cache_key = _cache_key(
            doc_id,
            "agent_role",
            role=role_name,
            format_ver=AGENT_OUTPUT_FORMAT_VERSION,
            role_sig=_hash_text(role.title + role.mission + "||".join(role.checks)),
            retrieval=int(bool(use_retrieval)),
            text_sig=_hash_text(contract_text_for_agents),
            contract_type=effective_contract_type,
            evidence_sig=_hash_text(evidence_signals),
            extraction_sig=_hash_text(validated_extraction),
        )
        cached_role_output = retrieve_analysis_artifact(role_cache_key)
        if isinstance(cached_role_output, str) and cached_role_output.strip():
            return role_name, cached_role_output

        role_context = ""
        if use_retrieval:
            retrieval_query = f"{role_name} risk analysis for contract obligations"
            role_context = retrieve_context(retrieval_query, doc_id=doc_id, k=1)
        base_predict = _env_int("CLAUSEAI_AGENT_NUM_PREDICT", 500, minimum=400)
        retry_steps = (0,)
        role_output = ""
        for bump in retry_steps:
            role_output = run_role_agent(
                role_name,
                contract_text_for_agents,
                retrieved_context=role_context,
                num_predict=base_predict + bump,
                contract_type=effective_contract_type,
                evidence_signals=evidence_signals,
                validated_extraction=validated_extraction,
            )
            if not _is_likely_truncated_agent_output(role_output):
                break
        normalized_output = _coerce_agent_output(role_output)
        store_analysis_artifact(role_cache_key, normalized_output)
        return role_name, normalized_output

    max_workers = min(agent_plan.max_workers, max(1, len(ordered_roles)))
    role_output_map = {}
    emitted_stage_names = set()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_run_single_role, role_name): role_name for role_name in ordered_roles}
        for future in as_completed(future_map):
            role_name = future_map[future]
            try:
                role_name, role_output = future.result()
            except Exception as err:
                role_output = _agent_error_fallback(role_name, err)
            role_output_map[role_name] = role_output
            stage_name = agent_plan.stage_by_role.get(role_name)
            if stage_name and stage_name not in emitted_stage_names:
                _emit(stage_name)
                emitted_stage_names.add(stage_name)

    for stage_name in agent_plan.ordered_stages:
        if stage_name not in emitted_stage_names:
            _emit(stage_name)
    _emit("Aggregating responses...")
    return {role_name: role_output_map[role_name] for role_name in ordered_roles if role_name in role_output_map}
