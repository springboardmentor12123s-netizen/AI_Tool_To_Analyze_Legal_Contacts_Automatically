import os
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any, Dict, List, Optional, Union

USE_MOCK = False
USE_LOCAL_LLM = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq").lower() in ("ollama", "local")


# Return a structured fallback so the UI does not break when API quota is exhausted.
def _quota_fallback_response() -> str:
    return (
        "Key Clauses:\n- Not generated because OpenAI API quota is exhausted.\n\n"
        "Risks:\n- Analysis stopped due to insufficient API quota.\n\n"
        "Missing / Weak:\n- Add billing/credits or switch to local Ollama mode.\n\n"
        "Plain Summary:\nOpenAI returned 429 insufficient_quota, so this run could not complete.\n\n"
        "Risk Score: Not stated"
    )


# This class stores each agent's name, goal, and checklist.
@dataclass(frozen=True)
class AnalystRole:
    title: str
    mission: str
    checks: List[str]


ANALYST_ROLES: Dict[str, AnalystRole] = {
    "compliance": AnalystRole(
        title="Compliance Analyst",
        mission="Check regulatory, privacy, and policy alignment risks.",
        checks=[
            "Data privacy and security obligations",
            "Industry and jurisdiction regulatory references",
            "Audit, reporting, and policy adherence language",
        ],
    ),
    "finance": AnalystRole(
        title="Finance Analyst",
        mission="Review commercial risk, payment terms, and cost exposure.",
        checks=[
            "Payment schedule and late payment penalties",
            "Liability caps and indemnity economics",
            "Termination fees and renewal cost exposure",
        ],
    ),
    "legal": AnalystRole(
        title="Legal Analyst",
        mission="Evaluate enforceability, legal risk, and dispute posture.",
        checks=[
            "Governing law and dispute resolution",
            "Termination, breach, and remedy clauses",
            "Ambiguous or conflicting obligations",
        ],
    ),
    "operations": AnalystRole(
        title="Operations Analyst",
        mission="Assess delivery practicality, SLAs, and execution risk.",
        checks=[
            "Service levels, timelines, and milestones",
            "Roles, dependencies, and handoff assumptions",
            "Change management and escalation paths",
        ],
    ),
}


# Ask Ollama once and get the full answer at once.
def _ollama_chat_once(prompt: str, num_predict: int = 260) -> str:
    import requests

    model = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")
    url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/chat")
    connect_timeout = float(os.getenv("LOCAL_LLM_CONNECT_TIMEOUT", "10"))
    read_timeout = float(os.getenv("LOCAL_LLM_READ_TIMEOUT", "240"))
    max_retries = max(0, int(os.getenv("LOCAL_LLM_MAX_RETRIES", "1")))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a legal contract analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "options": {"num_predict": num_predict},
        "stream": False,
    }

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=(connect_timeout, read_timeout))
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except requests.exceptions.ReadTimeout as err:
            last_err = err
            if attempt >= max_retries:
                raise
            time.sleep(0.5 * (attempt + 1))
    if last_err:
        raise last_err
    return ""


# Stream Ollama text piece by piece so the UI can show live output.
def _ollama_chat_stream(prompt: str, num_predict: int = 260):
    import json
    import requests

    model = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")
    url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/chat")
    connect_timeout = float(os.getenv("LOCAL_LLM_CONNECT_TIMEOUT", "10"))
    read_timeout = float(os.getenv("LOCAL_LLM_READ_TIMEOUT", "240"))
    max_retries = max(0, int(os.getenv("LOCAL_LLM_MAX_RETRIES", "1")))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a legal contract analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "options": {"num_predict": num_predict},
        "stream": True,
    }

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, stream=True, timeout=(connect_timeout, read_timeout))
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "message" in data and "content" in data["message"]:
                    yield data["message"]["content"]
                if data.get("done"):
                    return
            return
        except requests.exceptions.ReadTimeout as err:
            last_err = err
            if attempt >= max_retries:
                raise
            time.sleep(0.5 * (attempt + 1))
    if last_err:
        raise last_err


def _llm_system_prompt() -> str:
    return "You are a legal contract analysis assistant."


def _is_rate_limit_error(err: Exception) -> bool:
    text = str(err).lower()
    return "rate limit" in text or "rate_limit_exceeded" in text or "429" in text


def _extract_retry_after_seconds(err: Exception) -> float:
    text = str(err)
    match = re.search(r"try again in\s+([0-9.]+)s", text, flags=re.IGNORECASE)
    if match:
        try:
            return max(0.0, float(match.group(1)))
        except ValueError:
            return 0.0
    return 0.0


def _is_connection_error(err: Exception) -> bool:
    text = str(err).lower()
    return (
        "apiconnectionerror" in text
        or "connection error" in text
        or "connection reset" in text
        or "temporarily unavailable" in text
        or "timed out" in text
        or "timeout" in text
    )


def _connection_fallback_response() -> str:
    return (
        "Key Clauses:\n- Not generated because the provider connection failed.\n\n"
        "Risks:\n- Analysis may be incomplete due to network/provider interruption.\n\n"
        "Missing / Weak:\n- Retry in a few seconds and verify internet/API status.\n\n"
        "Plain Summary:\nModel connection failed during this run, so a safe fallback was returned.\n\n"
        "Risk Score: Not stated"
    )


def _rate_limit_fallback_response() -> str:
    return (
        "Key Clauses:\n- Not generated because the model request was rate-limited.\n\n"
        "Risks:\n- Some risks may be missing due to temporary throughput limits.\n\n"
        "Missing / Weak:\n- Retry after a short wait or reduce concurrent workers.\n\n"
        "Plain Summary:\nAnalysis hit provider rate limits and returned a partial-safe fallback.\n\n"
        "Risk Score: Not stated"
    )


@lru_cache(maxsize=1)
def _get_groq_client():
    from openai import OpenAI
    from config.config import GROQ_API_KEY

    if not GROQ_API_KEY:
        return None
    return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


def _groq_chat_once(prompt: str, num_predict: int = 260) -> str:
    from config.config import GROQ_MODEL

    client = _get_groq_client()
    if client is None:
        raise RuntimeError("Missing GROQ_API_KEY. Set it in your .env file.")

    max_retries = max(0, int(os.getenv("CLAUSEAI_GROQ_MAX_RETRIES", "3")))
    backoff_base = float(os.getenv("CLAUSEAI_GROQ_BACKOFF_BASE", "1.0"))
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": _llm_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=num_predict,
            )
            return response.choices[0].message.content or ""
        except Exception as err:
            last_err = err
            if attempt >= max_retries:
                break
            if _is_rate_limit_error(err):
                retry_after = _extract_retry_after_seconds(err)
                sleep_s = retry_after if retry_after > 0 else backoff_base * (attempt + 1)
                time.sleep(min(20.0, max(0.2, sleep_s)))
                continue
            if _is_connection_error(err):
                sleep_s = backoff_base * (attempt + 1)
                time.sleep(min(10.0, max(0.2, sleep_s)))
                continue
            break
    if last_err:
        raise last_err
    return ""


def _groq_chat_stream(prompt: str, num_predict: int = 260):
    from config.config import GROQ_MODEL

    client = _get_groq_client()
    if client is None:
        raise RuntimeError("Missing GROQ_API_KEY. Set it in your .env file.")

    stream = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": _llm_system_prompt()},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=num_predict,
        stream=True,
    )
    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = getattr(chunk.choices[0], "delta", None)
        if delta and getattr(delta, "content", None):
            yield delta.content


# Pick which model source to use: mock, Groq, local Ollama, or OpenAI.
def get_llm_response(prompt: str, num_predict: int = 260) -> str:
    if USE_MOCK:
        return (
            "Key Clauses:\n- Parties and scope\n\n"
            "Risks:\n- Missing dispute resolution\n\n"
            "Missing / Weak:\n- No privacy clause\n\n"
            "Plain Summary:\nContract is usable but has material legal gaps."
        )

    provider = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq").lower()

    if provider in ("ollama", "local"):
        return _ollama_chat_once(prompt, num_predict=num_predict)
    if provider == "groq":
        try:
            return _groq_chat_once(prompt, num_predict=num_predict)
        except Exception as err:
            if _is_rate_limit_error(err):
                return _rate_limit_fallback_response()
            if _is_connection_error(err):
                return _connection_fallback_response()
            raise

    from openai import OpenAI
    from config.config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a legal contract analysis assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=num_predict,
        )
        return response.choices[0].message.content or ""
    except Exception as err:
        # Handle exhausted quota gracefully so Streamlit does not show a hard crash.
        if "insufficient_quota" in str(err) or "429" in str(err):
            return _quota_fallback_response()
        raise


# Return output as a stream so the caller can read chunks safely.
def get_llm_response_stream(prompt: str, num_predict: int = 260):
    if USE_MOCK:
        yield get_llm_response(prompt, num_predict=num_predict)
        return
    provider = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq").lower()
    if provider in ("ollama", "local"):
        yield from _ollama_chat_stream(prompt, num_predict=num_predict)
        return
    if provider == "groq":
        try:
            yield from _groq_chat_stream(prompt, num_predict=num_predict)
            return
        except Exception as err:
            if _is_rate_limit_error(err):
                yield _rate_limit_fallback_response()
                return
            if _is_connection_error(err):
                yield _connection_fallback_response()
                return
            raise
    yield get_llm_response(prompt, num_predict=num_predict)


# Convert role data into a simple dict format for other parts of the app.
def get_role_structure() -> Dict[str, Dict[str, Union[str, List[str]]]]:
    return {
        role_name: {
            "title": role.title,
            "mission": role.mission,
            "checks": role.checks,
        }
        for role_name, role in ANALYST_ROLES.items()
    }


@lru_cache(maxsize=1)
def _get_hf_embedder():
    from config.config import HF_EMBEDDING_MODEL

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    return SentenceTransformer(HF_EMBEDDING_MODEL)


def _as_vector(raw_embedding: Any) -> List[float]:
    # Handles list, tuple, numpy array, and tensor-like outputs.
    if hasattr(raw_embedding, "tolist"):
        values = raw_embedding.tolist()
    else:
        values = raw_embedding
    return [float(v) for v in values]


_DOC_EMBED_INDEX: Dict[str, Dict[str, Any]] = {}
_DOC_EMBED_INDEX_LOCK = Lock()


# Quick check to see if vector search is ready to use.
def vectorstore_available() -> bool:
    return _get_hf_embedder() is not None


# Save contract chunks with doc info so we can search the right contract later.
def index_contract_chunks(chunks: List[str], doc_id: str) -> bool:
    embedder = _get_hf_embedder()
    if embedder is None or not chunks:
        return False
    embeddings = embedder.encode(chunks, normalize_embeddings=True)
    vectors = [_as_vector(item) for item in embeddings]
    with _DOC_EMBED_INDEX_LOCK:
        _DOC_EMBED_INDEX[doc_id] = {"chunks": chunks, "vectors": vectors}
    return True


# Fetch most relevant saved chunks to give the agent better context.
def retrieve_context(query: str, doc_id: Optional[str] = None, k: int = 3) -> str:
    embedder = _get_hf_embedder()
    if embedder is None or not doc_id:
        return ""
    with _DOC_EMBED_INDEX_LOCK:
        doc_record = _DOC_EMBED_INDEX.get(doc_id)
    if not doc_record:
        return ""

    query_vec = _as_vector(embedder.encode(query, normalize_embeddings=True))
    scored_chunks = []
    for idx, chunk_vec in enumerate(doc_record["vectors"]):
        # With normalized vectors, dot product gives cosine similarity.
        score = sum(a * b for a, b in zip(query_vec, chunk_vec))
        scored_chunks.append((score, idx))
    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    top_chunks = [doc_record["chunks"][idx] for _, idx in scored_chunks[: max(1, k)]]
    return "\n\n".join(top_chunks)


# Run one specialist agent and return its findings.
def run_role_agent(
    role_name: str,
    contract_text: str,
    retrieved_context: str = "",
    num_predict: int = 180,
    peer_context: str = "",
    turn_number: int = 1,
    max_turns: int = 1,
) -> str:
    role = ANALYST_ROLES[role_name]
    checks = "\n".join(f"- {item}" for item in role.checks)
    context_block = f"\nRelevant retrieved context:\n{retrieved_context}\n" if retrieved_context else ""
    peer_context_block = ""
    if peer_context:
        peer_context_block = (
            f"\nPeer analyst notes from prior round (turn {turn_number - 1} of {max_turns}):\n"
            f"{peer_context}\n"
        )
    interaction_rule = (
        "- Reconcile with peer notes: keep agreements, call out conflicts, and update your own bullets only where needed."
        if peer_context
        else "- Focus only on your domain checklist."
    )

    prompt = f"""
You are acting as: {role.title}
Mission: {role.mission}
Current turn: {turn_number} of {max_turns}

Your checklist:
{checks}

Analyze this contract text and output:
1) Findings (max 4 bullets)
2) Risks (max 3 bullets)
3) Missing / Weak points (max 3 bullets)
4) Recommended follow-up actions (max 3 bullets)

Rules:
- Use only the provided contract text.
- Be concise and practical.
- Keep each bullet to one short sentence.
- Do not add empty lines between bullets or sections.
- Say "Not stated" when information is missing.
- Do not quote long passages.
- Keep findings specific to your role, even when peer notes include other domains.
- {interaction_rule}
- No preface or closing line.
{context_block}
{peer_context_block}
Contract text:
{contract_text}
"""
    return get_llm_response(prompt, num_predict=num_predict)

