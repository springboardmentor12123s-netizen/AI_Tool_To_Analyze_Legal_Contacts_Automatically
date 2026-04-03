# Keep prompt construction centralized so each analysis step stays focused and easy to tune.
BASE_ANALYSIS_PROMPT = """
You are a contract analysis assistant with expert-level legal knowledge.

Analyze the contract carefully and extract key information with HIGH ACCURACY.

IMPORTANT RULES:
- Read the ENTIRE contract before answering
- Focus on the most important clauses first
- Quote exact text from the contract as evidence where possible

PRIORITY ORDER (STRICT):

1. Salary / compensation
2. Termination conditions
3. Probation period
4. Notice period
5. Non-compete / restrictions
6. Governing law / jurisdiction
7. Confidentiality / IP
8. Then other details

If any of the above exist, they MUST be included before lower-priority details.

Rules:

* Use only the contract text - do NOT hallucinate
* Use "Not stated" only when the contract genuinely does not contain the information after checking the full text
* Be concise but thorough
* If a clause exists in the contract, do not mark it as missing
* Before marking any clause as missing, check whether it is relevant to the document type
* If a clause is not relevant to the document type, treat it as "Not applicable for this document type"
* Do not mark non-applicable clauses as missing
* Mention missing or weak points only when they are clearly missing or unclear
* Focus on the most important business and legal terms for the contract type
* No intro and no extra explanation outside the requested structure
* Cross-verify each finding against the contract text before finalizing
* Provide a thorough, accurate analysis
* For every risk or finding, quote the exact text from the document
* Rate each risk as Critical, High, Medium, or Low
* Prefer extracting concrete clauses, figures, dates, and obligations over saying "Not stated"
* Do not return mostly "Not stated" if the contract contains substantive clauses

Report cleaning rules:

* Remove duplicates and merge similar risks or issues into one point
* Do not include "Not applicable" items in the final report
* Use only Critical / High / Medium / Low for risk rating
* Limit critical issues to the most important 4 to 5 points
* Keep the output clear, concise, and free of repetition
""".strip()

FEW_SHOT_EXAMPLE = """
Example output:
Key Clauses:
- Compensation is stated as a fixed annual salary of INR 12,00,000 payable monthly.
- Termination allows either party to end the agreement with 30 days written notice.
- Confidentiality obligations survive termination for 2 years.
- Non-compete clause restricts employment with competitors for 1 year within India.
- Governing law is the laws of the State of Karnataka, India.
- Probation period is 6 months from the date of joining.

Risks:
- Non-compete clause may be overly broad and potentially unenforceable.
- No clear liability cap is defined for either party.
- Termination for cause does not specify what constitutes "cause".

Missing / Weak:
- No clear dispute resolution mechanism (arbitration or mediation) is stated.
- No data protection or privacy clause despite handling personal information.

Plain Summary:
This employment contract sets out a fixed annual compensation of INR 12,00,000 with a 6-month probation period. Either party may terminate with 30 days notice. The agreement includes confidentiality and non-compete restrictions but lacks dispute resolution and data privacy provisions. The non-compete scope may face enforceability challenges.

Risk Score:
Medium
""".strip()

REASONING_GUARDRAILS = """
Internal reasoning protocol:
- First identify the contract type and the clauses that are material for that type.
- Scan the FULL document before drafting any finding.
- Cross-check every conclusion against the exact contract text before finalizing.
- Prefer exact textual evidence over inference when there is any ambiguity.
- Resolve conflicts by favoring the clearer clause and noting uncertainty only when necessary.
- Think step by step internally, but return only the requested final answer format.
- Before finalizing, re-read each bullet point and verify it is supported by the contract text.
- If the document text is truncated (indicated by [...document continues...]), note which sections may be incomplete.
- NEVER say "Not stated" if the information exists anywhere in the provided text.
- ALWAYS quote the exact clause number or section heading when referencing contract provisions.
""".strip()


def _contract_type_rules(contract_type: str) -> str:
    value = (contract_type or "").strip().lower()
    if "lease" in value:
        return """
- This is a lease-style agreement.
- Prioritize lease term, rent, deposit, permitted use, maintenance, utilities, entry rights, subletting, termination, governing law, and jurisdiction.
- Ignore confidentiality, data privacy, service levels, liability caps, renewal cost exposure, termination fees, audit, and software vendor-style risks unless the lease text clearly includes them.
""".strip()
    if "nda" in value:
        return """
- This is an NDA-style agreement.
- Prioritize confidential information scope, exclusions, permitted use, disclosure limits, return or destruction, term, remedies, governing law, and jurisdiction.
- Do not introduce payment, service levels, or delivery obligations unless the text clearly includes them.
""".strip()
    if "employment" in value:
        return """
- This is an employment-style agreement.
- Prioritize duties, compensation/salary, leave, confidentiality, IP, termination, probation, notice period, restrictive covenants, governing law, and dispute handling.
- Extract EXACT salary figures, probation duration, and notice periods.
- Do NOT include service levels, SLAs, change management, delivery timelines, or vendor-style risks.
""".strip()
    if "msa" in value:
        return """
- This is an MSA or services-style agreement.
- Prioritize scope, fees, payment, SLAs, change control, liability, indemnity, confidentiality, data handling, termination, governing law, and dispute handling.
""".strip()
    return """
- Prioritize only clauses clearly supported by the contract text.
- Do not infer industry-specific obligations unless explicitly present.
""".strip()

def build_fast_summary_prompt(contract_text: str) -> str:
    return f"""
{BASE_ANALYSIS_PROMPT}

Task:
- Produce a plain-English contract summary for a busy reader.

Output rules:
- 6 sentences max
- 600 words max
- Mention the core purpose, key obligation, major risk, and any obvious gap if clearly supported
- Do NOT repeat clauses verbatim
- Make it useful for decision-making
- No bullets
- Prefer concrete facts from the contract over generic statements

Contract text:
{contract_text}
""".strip()


def build_evidence_extraction_prompt(contract_text: str) -> str:
    return f"""
You are a high-accuracy contract analysis AI.

Analyze the document carefully and produce correct, consistent, and evidence-based extraction.

{REASONING_GUARDRAILS}

Rules:
- Use only the contract text
- Always scan the full document before answering
- Search the full document before marking anything missing
- Do not hallucinate or assume
- Evidence must be exact text copied from the document
- If a field is not clearly found, set value to "Not clearly found" and evidence to ""
- Focus on accuracy over speed
- Prefer returning actual extracted values over "Not clearly found" whenever the text supports them

Step 1: detect the document type first, such as Employment Contract, Lease Agreement, NDA, Training Agreement, or similar.

Adjust expectations by document type:
- Employment: prioritize salary, probation, notice, non-compete, termination, governing law
- Lease: prioritize rent, deposit, lease term, notice, restrictions, termination, governing law
- Do not treat irrelevant fields as missing
- If a field is not relevant for the document type, set its value to "Not applicable for this document type" and evidence to ""

Step 2: check for placeholders before finalizing any value.

Placeholder examples:
- [Amount]
- [Notice Period]
- [Duration]
- [Company Name]
- [Jurisdiction]

If a placeholder is present instead of completed information:
- set value to "Not clearly specified (placeholder present)"
- set evidence to the exact placeholder text
- do not treat the placeholder as valid data

Return exactly this JSON object shape:
{{
  "document_type": {{"value": "", "evidence": ""}},
  "salary": {{"value": "", "evidence": ""}},
  "probation_period": {{"value": "", "evidence": ""}},
  "notice_period_probation": {{"value": "", "evidence": ""}},
  "notice_period_post_probation": {{"value": "", "evidence": ""}},
  "termination_conditions": {{"value": "", "evidence": ""}},
  "non_compete": {{"value": "", "evidence": ""}},
  "governing_law": {{"value": "", "evidence": ""}}
}}

Validation:
- Re-check the document before answering
- Ensure salary, notice periods, termination, non-compete, and governing law are not missed if clearly present
- Ensure evidence supports each non-empty value
- Ensure placeholders are not treated as real values
- Ensure fields irrelevant to the document type are marked "Not applicable for this document type"
- Before finalizing, internally compare the extracted values against the strongest supporting evidence one more time.

{FEW_SHOT_EXAMPLE}

Contract text:
{contract_text}
""".strip()


def build_direct_analysis_prompt(
    contract_text: str,
    length_rule: str,
    risk_rule: str,
    contract_hint: str,
    format_rule: str,
    language_rule: str,
    contract_type: str = "Auto-detect",
    evidence_signals: str = "",
    validated_extraction: str = "",
) -> str:
    extraction_block = (
        f"\nValidated key field extraction:\n{validated_extraction}\n"
        if validated_extraction
        else ""
    )
    return f"""
{BASE_ANALYSIS_PROMPT}

{REASONING_GUARDRAILS}

Task:
- Analyze this contract directly and produce one final answer.

Behavior rules:
- {length_rule}
- {risk_rule}
- {contract_hint}
- {format_rule}
- {language_rule}
- Prefer the most material issues over exhaustive coverage
- Avoid verbatim copying - paraphrase with precision
- Use only the contract text
- Use "Not stated" only when the contract genuinely does not contain the information
- For employment contracts, ALWAYS include salary/compensation, termination, probation, notice period, non-compete, and governing law when present
- Prefer extracting concrete clauses over saying "Not stated"
- For every finding, include a short supporting quote, clause label, section reference, or exact phrase from the document

Final check:
- Ensure nothing listed as missing is already present in the contract
- Ensure there are no contradictions between sections
- If unsure about a point, leave it out or say "Not stated"
- Cross-check the final answer against the validated extraction before returning it

Contract-type rules:
{_contract_type_rules(contract_type)}
{extraction_block}

Format enforcement:
- Keep sections separate and easy to scan
- If using bullets, each bullet must begin with "- "
- Plain Summary should be simple and practical

Return exactly these sections:
Key Clauses:
- ...

Risks:
- ...

Missing / Weak:
- ...

Plain Summary:
...

Risk Score:
Critical | High | Medium | Low

Section limits:
- Key Clauses: max 6 bullets (include ALL important clauses)
- Risks: max 5 bullets
- Missing / Weak: max 4 bullets, or write "Not stated" if none are clear
- Plain Summary: up to 600 words

{FEW_SHOT_EXAMPLE}

Contract text:
{contract_text}
""".strip()


def build_turbo_analysis_prompt(
    contract_text: str,
    extracted_signals: str,
    retrieved_context: str,
    length_rule: str,
    risk_rule: str,
    contract_hint: str,
    format_rule: str,
    language_rule: str,
    contract_type: str = "Auto-detect",
    validated_extraction: str = "",
) -> str:
    extraction_block = (
        f"\nValidated key field extraction:\n{validated_extraction}\n"
        if validated_extraction
        else ""
    )
    return f"""
{BASE_ANALYSIS_PROMPT}

{REASONING_GUARDRAILS}

Task:
- Turbo analysis mode: synthesize pre-extracted signals and retrieved context into one final answer.

Behavior rules:
- {length_rule}
- {risk_rule}
- {contract_hint}
- {format_rule}
- {language_rule}
- Resolve conflicts between signals and contract text in favor of the clearer clause
- Use only the contract text and provided analysis
- Quote exact values (salary, dates, durations) from the contract
- Provide a thorough, accurate analysis
- For every risk or finding, quote the exact text from the document
- Rate each risk as Critical, High, Medium, or Low
- Prefer extracting concrete clauses over saying "Not stated"
- Do not return mostly "Not stated" if the contract contains substantive clauses

Final check:
- Ensure nothing listed as missing is already present in the contract
- Cross-check against extracted signals
- Verify each Key Clause bullet is supported by the contract text

Contract-type rules:
{_contract_type_rules(contract_type)}
{extraction_block}

Pre-extracted signals:
{extracted_signals}

Retrieved context:
{retrieved_context}

Return exactly these sections:
Key Clauses:
- ...

Risks:
- ...

Missing / Weak:
- ...

Plain Summary:
...

Risk Score:
Critical | High | Medium | Low

Section limits:
- Key Clauses: max 6 bullets
- Risks: max 5 bullets
- Missing / Weak: max 4 bullets
- Plain Summary: up to 600 words

{FEW_SHOT_EXAMPLE}

Contract text:
{contract_text}
""".strip()


def build_clause_extraction_prompt(
    role_title: str = "",
    checks: str = "",
    contract_text: str = "",
    retrieved_context: str = "",
    contract_type: str = "Auto-detect",
    evidence_signals: str = "",
    validated_extraction: str = "",
    focus_areas: str = "",
) -> str:
    context_block = f"\nRetrieved context:\n{retrieved_context}\n" if retrieved_context else ""
    signals_block = f"\nEvidence signals:\n{evidence_signals}\n" if evidence_signals else ""
    extraction_block = (
        f"\nValidated key field extraction:\n{validated_extraction}\n"
        if validated_extraction
        else ""
    )
    focus_text = focus_areas or checks or "all material clauses"
    return f"""
    {BASE_ANALYSIS_PROMPT}

    Task:
    - Extract key clauses and relevant obligations from the contract text.
    - Focus on: {focus_text}
    - Include EXACT values (amounts, dates, durations, percentages) from the contract
    - You MUST quote the exact clause text from the document as evidence for every finding. Be specific - cite section numbers, clause numbers, or exact phrases. Do not make generic statements.

    Rules:
    - One bullet per clause
    - Include only material clauses supported by the text
    - Do not repeat or paraphrase the same clause twice
    - Quote specific figures and terms
    - List up to 6 key clauses
    - Keep the total response within 600 words
    - Prefer actual clauses from the document over saying "Not stated"

    Contract-type rules:
    {_contract_type_rules(contract_type)}
    {extraction_block}
    {context_block}{signals_block}

    Return only:
    Key Clauses:
    - ...

Contract text:
{contract_text}
""".strip()


def build_role_analysis_prompt(
    role_title: str,
    mission: str,
    checks: str,
    contract_text: str,
    retrieved_context: str = "",
    peer_context: str = "",
    turn_number: int = 1,
    max_turns: int = 1,
    contract_type: str = "Auto-detect",
    evidence_signals: str = "",
    validated_extraction: str = "",
) -> str:
    peer_block = ""
    extraction_block = (
        f"\nValidated key field extraction:\n{validated_extraction}\n"
        if validated_extraction
        else ""
    )
    context_block = f"\nRetrieved context:\n{retrieved_context}\n" if retrieved_context else ""
    signals_block = f"\nEvidence signals:\n{evidence_signals}\n" if evidence_signals else ""
    interaction_rule = "- Focus only on your role checklist."
    if peer_context:
        peer_block = f"\nPeer analyst notes from turn {turn_number - 1} of {max_turns}:\n{peer_context}\n"
        interaction_rule = (
            "- Reconcile with peer notes: keep agreements, note conflicts briefly, and update only your own role output."
        )
    return f"""
{BASE_ANALYSIS_PROMPT}

{REASONING_GUARDRAILS}

Role:
- {role_title}
- Mission: {mission}
- Turn: {turn_number} of {max_turns}

Checklist:
{checks}

RULES:
- Read the FULL contract before answering
- Quote exact text as evidence where possible
- Do NOT hallucinate - only cite what exists
- Each finding must be directly supported by the contract text
- You MUST quote the exact clause text from the document as evidence for every finding. Be specific - cite section numbers, clause numbers, or exact phrases. Do not make generic statements.
- If no issue exists for a checklist item, skip it rather than inventing one
- Stay specific to this role
- Do not quote long passages
- Prefer concrete obligations, risks, and missing language
- For employment contracts, prioritize compensation, term, notice, termination, restrictions, and governing law when clearly present
- If something is not clearly present, write "Not stated" or leave it out
- STRICT VALIDATION: before adding a "Missing / Weak point", check contract text; if found, do not include it
- CONSISTENCY RULE: if you list something in Findings, it cannot appear in Missing / Weak points
- Do not list irrelevant risks for the contract type
- Only include missing items that are both completely absent and commonly expected for this contract type
- Prefer concrete findings from the document over "Not stated"
- {interaction_rule}
- No extra commentary

Contract-type rules:
{_contract_type_rules(contract_type)}
{extraction_block}
{context_block}{signals_block}
{peer_block}

Return exactly:
Findings:
- [specific finding with evidence from the contract, max 6 bullets]

Risks:
- [specific risk with impact and exact evidence, max 5 bullets]

Missing / Weak points:
- [what is missing or unclear, max 4 bullets]

Recommended follow-up actions:
- [actionable next step, max 4 bullets]

Section rules:
- Each bullet must be a complete, non-truncated sentence ending with a period
- Findings: max 6 bullets
- Risks: max 5 bullets
- Missing / Weak points: max 4 bullets
- Recommended follow-up actions: max 4 bullets

Contract text:
{contract_text}
""".strip()


def build_synthesis_prompt(
    contract_text: str,
    clause_extracts: str,
    analyst_notes: str,
    length_rule: str,
    risk_rule: str,
    contract_hint: str,
    format_rule: str,
    language_rule: str,
    contract_type: str = "Auto-detect",
    evidence_signals: str = "",
    validated_extraction: str = "",
) -> str:
    extraction_block = (
        f"\nValidated key field extraction:\n{validated_extraction}\n"
        if validated_extraction
        else ""
    )
    return f"""
{BASE_ANALYSIS_PROMPT}

{REASONING_GUARDRAILS}

Task:
- Combine the specialist notes into one final contract assessment.

Behavior rules:
- {length_rule}
- {risk_rule}
- {contract_hint}
- {format_rule}
- {language_rule}
- Resolve overlap and keep only the most material points
- Use clause extracts and analyst notes only as drafting aids
- Avoid verbatim copying
- Use only the contract text for factual claims
- Use "Not stated" only when the contract genuinely does not contain the information
- For employment contracts, prioritize salary / compensation, termination conditions, probation period, notice period, non-compete / restrictions, and governing law when clearly present
- Key Clauses must include salary if present
- Key Clauses must include termination or another legal-risk clause if present
- Provide a thorough, accurate analysis
- For every risk or finding, quote the exact text from the document
- Rate each risk as Critical, High, Medium, or Low
- Prefer extracting concrete clauses over saying "Not stated"

Final check:
- Ensure nothing listed as missing is already present in the contract
- Ensure there are no contradictions between sections
- If unsure about a point, leave it out or say "Not stated"
- Reconcile the final answer with the validated extraction and the strongest analyst evidence before returning it

Contract-type rules:
{_contract_type_rules(contract_type)}
{extraction_block}

Clause extracts:
{clause_extracts}

Analyst notes:
{analyst_notes}

{FEW_SHOT_EXAMPLE}

Format enforcement:
- Keep sections separate and easy to scan
- If using bullets, each bullet must begin with "- "
- Plain Summary should be simple and practical

Return exactly these sections:
Key Clauses:
- ...

Risks:
- ...

Missing / Weak:
- ...

Plain Summary:
...

Risk Score:
Critical | High | Medium | Low

Section limits:
- Key Clauses: max 6 bullets
- Risks: max 5 bullets
- Missing / Weak: max 4 bullets, or write "Not stated" if none are clear
- Plain Summary: up to 600 words
""".strip()
