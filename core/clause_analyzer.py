import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from core.document_loader import chunk_contract_text, parse_contract_text
from core.llm_engine import (
    ANALYST_ROLES,
    get_llm_response,
    get_llm_response_stream,
    index_contract_chunks,
    retrieve_context,
    run_role_agent,
    USE_LOCAL_LLM,
    vectorstore_available,
)
from core.planning_module import build_agent_execution_plan
from utils.prompts import LEGAL_ANALYSIS_PROMPT


# Parse integer env values safely so bad config does not break analysis.
def _env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default))
    try:
        return max(minimum, int(raw))
    except (TypeError, ValueError):
        return max(minimum, default)


# Analyze one contract end-to-end so the UI gets either final text or structured outputs.
def analyze_contract(
    pages,
    fast_mode: bool = False,
    stream: bool = False,
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
            "- Clause name: Not stated | Why it matters: Extraction failed due to temporary model throttling.\n"
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
        return marker_hits < 2

    def _coerce_agent_output(text: str) -> str:
        body = (text or "").strip()
        if not body:
            body = "Not stated."
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

        def _fmt(section_name: str):
            items = sections[section_name]
            if not items:
                return ["- Not stated"]
            cleaned = []
            for item in items[:4]:
                value = item.rstrip(". ")
                if value.endswith("..."):
                    value = value[:-3].rstrip()
                cleaned.append(value if value.startswith("-") else f"- {value}.")
            return cleaned

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
            body = "Not stated."

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
        risk_score = "Risk Score: Not stated"
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

        if not any(sections.values()):
            sections["Plain Summary"] = [body]

        def _auto_plain_summary() -> str:
            key = sections["Key Clauses"][0] if sections["Key Clauses"] else ""
            risk = sections["Risks"][0] if sections["Risks"] else ""
            if key and risk:
                return f"{key} Also, {risk}"
            if key:
                return key
            if risk:
                return f"Primary concern: {risk}"
            return "Summary generated from available findings is limited."

        def _fmt(section_name: str):
            items = sections[section_name]
            if not items:
                if section_name == "Plain Summary":
                    return [_auto_plain_summary()]
                return ["- Not stated"]
            if section_name == "Plain Summary":
                return [" ".join(items)[:400]]
            return [item if item.startswith("-") else f"- {item}" for item in items[:4]]

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
            body = "Not stated."
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

        def _fmt(section_name: str):
            items = sections[section_name]
            if not items:
                return ["- Not stated"]
            cleaned = []
            for item in items[:4]:
                value = item.rstrip(". ")
                if value.endswith("..."):
                    value = value[:-3].rstrip()
                cleaned.append(value if value.startswith("-") else f"- {value}.")
            return cleaned

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
        return _env_int("CLAUSEAI_AGENT_NUM_PREDICT", 180, minimum=100)

    contract_text = parse_contract_text(pages)
    contract_text_for_model = contract_text[:2200]
    contract_text_for_agents = contract_text[:1400]
    max_index_chunks = _env_int("CLAUSEAI_MAX_INDEX_CHUNKS", 8)
    deep_mode = os.getenv("CLAUSEAI_DEEP_ANALYSIS", "1") == "1"

    # Estimate token budget from verbosity settings to reduce truncation while staying fast.
    def _final_num_predict(
        summary_len: str,
        output_fmt: str,
        deep: bool = False,
        text_chars: int = 0,
    ) -> int:
        base = {"Short": 110, "Medium": 150, "Detailed": 220}.get(summary_len, 150)
        if output_fmt == "Summary only":
            base -= 30
        elif output_fmt == "Bullets + summary":
            base += 35
        elif output_fmt == "Bullets only":
            base += 20
        if text_chars and text_chars < 2500:
            base -= 20
        elif text_chars and text_chars > 9000:
            base += 30
        if deep:
            base += 30
        return max(90, base)

    agent_plan = build_agent_execution_plan(
        available_roles=ANALYST_ROLES,
        contract_text=contract_text,
        contract_type=contract_type,
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
            role_context = ""
            if use_retrieval_local:
                retrieval_query = f"{role_name} risk analysis for contract obligations"
                role_context = retrieve_context(retrieval_query, doc_id=doc_id_local, k=1)
            base_predict = _agent_num_predict()
            retry_steps = (0, 80, 140)
            role_output = ""
            for bump in retry_steps:
                role_output = run_role_agent(
                    role_name,
                    text_for_agents,
                    retrieved_context=role_context,
                    num_predict=base_predict + bump,
                )
                if not _is_likely_truncated_agent_output(role_output):
                    break
            return role_name, _coerce_agent_output(role_output)

        max_workers = min(agent_plan.max_workers, max(1, len(role_names_to_run)))
        role_output_map = {}
        emitted_stage_names = set()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(_run_single_role, role_name): role_name for role_name in role_names_to_run}
            for future in as_completed(future_map):
                role_name = future_map[future]
                try:
                    role_name, role_output = future.result()
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

        max_workers = min(agent_plan.max_workers, max(1, len(ordered_roles)))

        def _refine_turn(current_map, turn_idx: int):
            next_map = dict(current_map)

            def _run_single_role_refinement(role_name: str):
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

                base_predict = _agent_num_predict() + 30
                retry_steps = (0, 80)
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
                    )
                    if not _is_likely_truncated_agent_output(refined_output):
                        break
                return role_name, _coerce_agent_output(refined_output)

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_map = {
                    executor.submit(_run_single_role_refinement, role_name): role_name for role_name in ordered_roles
                }
                for future in as_completed(future_map):
                    role_name = future_map[future]
                    try:
                        role_name, role_output = future.result()
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
            role_context = ""
            if use_retrieval_local:
                retrieval_query = f"{role_name} key clause extraction from contract"
                role_context = retrieve_context(retrieval_query, doc_id=doc_id_local, k=2)
            context_block = f"\nRelevant retrieved context:\n{role_context}\n" if role_context else ""
            prompt = f"""
You are acting as: {role.title}
Mission: Extract key contract clauses relevant to your domain.

Focus areas:
{checks}

Return exactly this format:
Key Clauses:
- Clause name: <short name> | Why it matters: <1 sentence>
- Clause name: <short name> | Why it matters: <1 sentence>
- Clause name: <short name> | Why it matters: <1 sentence>

Missing / Weak:
- <1 sentence>
- <1 sentence>

Rules:
- Use only the provided text.
- Return max 3 key clauses.
- If no clause is found for a point, write: Not stated.
- No intro or closing text.
{context_block}
Contract text:
{text_for_model}
"""
            return role_name, get_llm_response(prompt, num_predict=140)

        configured_workers = os.getenv("CLAUSEAI_CLAUSE_WORKERS")
        if configured_workers and configured_workers.isdigit():
            worker_cap = max(1, int(configured_workers))
        else:
            worker_cap = 2 if USE_LOCAL_LLM else 4
        max_workers = min(worker_cap, max(1, len(role_names_to_run)))
        clause_output_map = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(_run_single_clause_extractor, role_name): role_name
                for role_name in role_names_to_run
            }
            for future in as_completed(future_map):
                role_name = future_map[future]
                try:
                    role_name, role_output = future.result()
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
        prompt = f"""
{LEGAL_ANALYSIS_PROMPT}

Provide a short, plain-English summary only.
Hard limits:
- 4 sentences max
- <= 120 words

Contract text:
{contract_text_for_model}
"""
        if stream:
            _emit("Finalizing results...")
            return get_llm_response_stream(prompt, num_predict=90)
        _emit("Finalizing results...")
        return get_llm_response(prompt, num_predict=90)

    # Deep analysis is the default path so retrieval + multi-agent synthesis runs by default.
    # Set CLAUSEAI_DEEP_ANALYSIS=0 only if you explicitly want the ultra-fast single-call path.
    if not deep_mode:
        _emit("Generating embeddings...")
        _emit("Detecting contract type...")
        _emit("Planning agent execution...")
        for stage_name in agent_plan.ordered_stages:
            _emit(stage_name)

        length_rule = {
            "Short": "Total output <= 120 words.",
            "Medium": "Total output <= 180 words.",
            "Detailed": "Total output <= 260 words.",
        }.get(summary_length, "Total output <= 180 words.")

        risk_rule = {
            "Conservative": "Flag more risks and ambiguities, even if minor.",
            "Balanced": "Flag meaningful risks and ambiguities only.",
            "Aggressive": "Only flag high-confidence, material risks.",
        }.get(risk_sensitivity, "Flag meaningful risks and ambiguities only.")

        contract_hint = (
            "If not clear, say 'Contract type unclear'."
            if contract_type == "Auto-detect"
            else f"Focus on {contract_type} contract patterns."
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

        final_prompt = f"""
{LEGAL_ANALYSIS_PROMPT}

Analyze this contract directly and produce the final response.
{length_rule}
{risk_rule}
{contract_hint}
{format_rule}
{language_rule}

Use these exact sections:
1) Key Clauses (max 3 bullets)
2) Risks (max 2 bullets)
3) Missing / Weak (max 2 bullets)
4) Plain Summary (max 2 short sentences)

Add one final line:
Risk Score: Low | Medium | High

If a point is missing, state "Not stated".
Avoid verbatim copying.

Contract text:
{contract_text_for_model}
"""

        if stream:
            _emit("Finalizing results...")
            return get_llm_response_stream(
                final_prompt,
                num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)),
            )
        _emit("Aggregating responses...")
        _emit("Finalizing results...")
        result = get_llm_response(
            final_prompt,
            num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)),
        )
        if output_format != "Summary only" and not _is_complete_output(result):
            # Retry once with a higher cap only when truncation is detected.
            result = get_llm_response(
                final_prompt,
                num_predict=_final_num_predict(summary_length, output_format, text_chars=len(contract_text_for_model)) + 80,
            )
        if output_format != "Summary only":
            result = _coerce_structured_output(result)
        if return_agent_outputs:
            role_output_map = _collect_agent_outputs(
                contract_text_for_agents,
                use_retrieval_local=False,
                doc_id_local=None,
                emit_progress=False,
            )
            role_output_map = _run_multi_turn_agent_interaction(
                role_output_map,
                contract_text_for_agents,
                use_retrieval_local=False,
                doc_id_local=None,
            )
            return {
                "final_output": result,
                "agent_outputs": _ordered_agent_output_dict(role_output_map),
            }
        return result

    doc_id = str(uuid.uuid4())
    use_retrieval = vectorstore_available()
    if use_retrieval:
        _emit("Generating embeddings...")
        chunks = chunk_contract_text(contract_text, chunk_size=1800, chunk_overlap=120)
        index_contract_chunks(chunks[:max_index_chunks], doc_id=doc_id)
    else:
        _emit("Generating embeddings...")
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
        if contract_type == "Auto-detect"
        else f"Focus on {contract_type} contract patterns."
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

    final_prompt = f"""
{LEGAL_ANALYSIS_PROMPT}

Synthesize the specialist analyst notes into one final response.
{length_rule}
{risk_rule}
{contract_hint}
{format_rule}
{language_rule}

Use these exact sections:
1) Key Clauses (max 3 bullets)
2) Risks (max 2 bullets)
3) Missing / Weak (max 2 bullets)
4) Plain Summary (max 2 short sentences)

Add one final line:
Risk Score: Low | Medium | High

If a point is missing, state "Not stated".
Avoid verbatim copying.

Domain clause extracts:
{chr(10).join(clause_outputs) if clause_outputs else "Not stated."}

Analyst notes:
{chr(10).join(role_outputs)}
"""

    if stream:
        _emit("Finalizing results...")
        return get_llm_response_stream(
            final_prompt,
            num_predict=_final_num_predict(
                summary_length,
                output_format,
                deep=True,
                text_chars=len(contract_text_for_model),
            ),
        )
    _emit("Finalizing results...")
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
    contract_text_for_agents = contract_text[:1400]
    max_index_chunks = _env_int("CLAUSEAI_MAX_INDEX_CHUNKS", 8)
    doc_id = str(uuid.uuid4())
    use_retrieval = vectorstore_available()
    if use_retrieval:
        _emit("Generating embeddings...")
        chunks = chunk_contract_text(contract_text, chunk_size=1800, chunk_overlap=120)
        index_contract_chunks(chunks[:max_index_chunks], doc_id=doc_id)
    else:
        _emit("Generating embeddings...")
    _emit("Detecting contract type...")
    _emit("Planning agent execution...")

    agent_plan = build_agent_execution_plan(
        available_roles=ANALYST_ROLES,
        contract_text=contract_text,
        contract_type=contract_type,
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
        return marker_hits < 2

    # Run one specialist role to keep threaded execution logic concise and reusable.
    def _run_single_role(role_name: str):
        role_context = ""
        if use_retrieval:
            retrieval_query = f"{role_name} risk analysis for contract obligations"
            role_context = retrieve_context(retrieval_query, doc_id=doc_id, k=1)
        base_predict = _env_int("CLAUSEAI_AGENT_NUM_PREDICT", 180, minimum=100)
        retry_steps = (0, 80, 140)
        role_output = ""
        for bump in retry_steps:
            role_output = run_role_agent(
                role_name,
                contract_text_for_agents,
                retrieved_context=role_context,
                num_predict=base_predict + bump,
            )
            if not _is_likely_truncated_agent_output(role_output):
                break
        return role_name, _coerce_agent_output(role_output)

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
