import hashlib
import importlib.util
import json
import os
import re
import time
import warnings
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock
from typing import Any, Dict, List, Optional, Union
from utils.prompts import build_role_analysis_prompt

USE_MOCK = False
USE_LOCAL_LLM = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq").lower() in ("ollama", "local")


def _default_num_predict() -> int:
    return max(1, int(os.getenv("CLAUSEAI_DEFAULT_NUM_PREDICT", "600")))


def _llm_temperature() -> float:
    try:
        return float(os.getenv("CLAUSEAI_TEMPERATURE", "0.15"))
    except ValueError:
        return 0.15


def _llm_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("CLAUSEAI_LLM_TIMEOUT_SECONDS", "25")))
    except ValueError:
        return 25.0


def _groq_max_tokens(num_predict: int) -> int:
    return min(max(1, num_predict), _default_num_predict())


# Return a structured fallback so the UI does not break when API quota is exhausted.
def _quota_fallback_response() -> str:
    return (
        "Key Clauses:\n- Analysis unavailable due to provider quota exhaustion.\n\n"
        "Risks:\n- No reliable AI risk analysis was generated for this run.\n\n"
        "Missing / Weak:\n- Add billing credits or switch provider, then retry.\n\n"
        "Plain Summary:\nTemporary AI provider failure. No contract analysis was generated.\n\n"
        "Risk Score: Unavailable"
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
def _ollama_chat_once(prompt: str, num_predict: int = 600) -> str:
    import requests

    model = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")
    url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/chat")
    timeout_s = _llm_timeout_seconds()
    connect_timeout = min(float(os.getenv("LOCAL_LLM_CONNECT_TIMEOUT", "10")), timeout_s)
    read_timeout = min(float(os.getenv("LOCAL_LLM_READ_TIMEOUT", "240")), timeout_s)
    max_retries = max(0, int(os.getenv("LOCAL_LLM_MAX_RETRIES", "1")))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a legal contract analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": _llm_temperature(),
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
def _ollama_chat_stream(prompt: str, num_predict: int = 600):
    import json
    import requests

    model = os.getenv("LOCAL_LLM_MODEL", "llama3.1:8b")
    url = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/chat")
    timeout_s = _llm_timeout_seconds()
    connect_timeout = min(float(os.getenv("LOCAL_LLM_CONNECT_TIMEOUT", "10")), timeout_s)
    read_timeout = min(float(os.getenv("LOCAL_LLM_READ_TIMEOUT", "240")), timeout_s)
    max_retries = max(0, int(os.getenv("LOCAL_LLM_MAX_RETRIES", "1")))

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a legal contract analysis assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": _llm_temperature(),
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


def _is_model_decommissioned_error(err: Exception) -> bool:
    text = str(err).lower()
    return "model_decommissioned" in text or "decommissioned and is no longer supported" in text


def _groq_fallback_models(primary_model: str) -> list[str]:
    configured = os.getenv(
        "CLAUSEAI_GROQ_FALLBACK_MODELS",
        "llama-3.3-70b-versatile,openai/gpt-oss-120b,llama-3.1-8b-instant",
    )
    ordered = []
    seen = set()
    for candidate in [primary_model, *configured.split(",")]:
        normalized = (candidate or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _connection_fallback_response() -> str:
    return (
        "Key Clauses:\n- Analysis unavailable due to provider connection failure.\n\n"
        "Risks:\n- No reliable AI risk analysis was generated for this run.\n\n"
        "Missing / Weak:\n- Retry in a few seconds and verify provider connectivity.\n\n"
        "Plain Summary:\nTemporary AI provider failure. No contract analysis was generated.\n\n"
        "Risk Score: Unavailable"
    )


def _is_insufficient_quota_error(err: Exception) -> bool:
    text = str(err).lower()
    return "insufficient_quota" in text or "exceeded your current quota" in text


def _rate_limit_fallback_response() -> str:
    return (
        "Key Clauses:\n- Analysis unavailable due to provider rate limiting.\n\n"
        "Risks:\n- No reliable AI risk analysis was generated for this run.\n\n"
        "Missing / Weak:\n- Retry after a short wait or reduce request volume.\n\n"
        "Plain Summary:\nTemporary AI provider failure. No contract analysis was generated.\n\n"
        "Risk Score: Unavailable"
    )


@lru_cache(maxsize=1)
def _get_groq_client():
    from openai import OpenAI
    from config.config import GROQ_API_KEY

    if not GROQ_API_KEY:
        return None
    return OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        timeout=_llm_timeout_seconds(),
    )


def _groq_chat_once(prompt: str, num_predict: int = 600) -> str:
    from config.config import GROQ_MODEL

    client = _get_groq_client()
    if client is None:
        raise RuntimeError("Missing GROQ_API_KEY. Set it in your .env file.")

    max_retries = max(0, int(os.getenv("CLAUSEAI_GROQ_MAX_RETRIES", "5")))
    backoff_base = float(os.getenv("CLAUSEAI_GROQ_BACKOFF_BASE", "3.0"))
    last_err = None
    fallback_models = _groq_fallback_models(GROQ_MODEL)
    with _GROQ_REQUEST_LOCK:
        for model_name in fallback_models:
            for attempt in range(max_retries + 1):
                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": _llm_system_prompt()},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=_llm_temperature(),
                        max_tokens=_groq_max_tokens(num_predict),
                    )
                    return response.choices[0].message.content or ""
                except Exception as err:
                    last_err = err
                    if _is_model_decommissioned_error(err):
                        break  # try next model
                    if attempt >= max_retries:
                        break
                    if _is_rate_limit_error(err):
                        retry_after = _extract_retry_after_seconds(err)
                        sleep_s = retry_after if retry_after > 0 else backoff_base * (2 ** attempt)
                        sleep_s = min(60.0, max(1.0, sleep_s))
                        warnings.warn(
                            f"[ClauseAI] Groq rate-limited on {model_name}, "
                            f"attempt {attempt+1}/{max_retries+1}, "
                            f"waiting {sleep_s:.1f}s before retry..."
                        )
                        time.sleep(sleep_s)
                        continue
                    if _is_connection_error(err):
                        sleep_s = backoff_base * (attempt + 1)
                        time.sleep(min(30.0, max(1.0, sleep_s)))
                        continue
                    break
    if last_err:
        raise last_err
    return ""


def _groq_chat_stream(prompt: str, num_predict: int = 600):
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
        temperature=_llm_temperature(),
        max_tokens=_groq_max_tokens(num_predict),
        stream=True,
    )
    for chunk in stream:
        if not getattr(chunk, "choices", None):
            continue
        delta = getattr(chunk.choices[0], "delta", None)
        if delta and getattr(delta, "content", None):
            yield delta.content


# Pick which model source to use: mock, Groq, local Ollama, or OpenAI.
def get_llm_response(prompt: str, num_predict: int = 600) -> str:
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
                raise RuntimeError(
                    f"Groq rate limit exceeded after all retries. "
                    f"Wait 1-2 minutes and try again. Error: {str(err)[:200]}"
                ) from err
            if _is_connection_error(err):
                raise RuntimeError(
                    f"Groq connection failed after all retries. "
                    f"Check your internet and API key. Error: {str(err)[:200]}"
                ) from err
            raise

    from openai import OpenAI
    from config.config import OPENAI_API_KEY

    client = OpenAI(api_key=OPENAI_API_KEY, timeout=_llm_timeout_seconds())
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a legal contract analysis assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=_llm_temperature(),
            max_tokens=num_predict,
        )
        return response.choices[0].message.content or ""
    except Exception as err:
        if "insufficient_quota" in str(err) or "429" in str(err):
            raise RuntimeError(
                f"OpenAI quota exhausted. Add billing credits. Error: {str(err)[:200]}"
            ) from err
        raise


def get_llm_response_high_quality(prompt: str, num_predict: int = 600) -> str:
    provider = os.getenv("CLAUSEAI_LLM_PROVIDER", "groq").lower()
    if provider == "groq":
        from openai import OpenAI
        from config.config import GROQ_API_KEY

        if not GROQ_API_KEY:
            return get_llm_response(prompt, num_predict=num_predict)

        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            timeout=_llm_timeout_seconds(),
        )
        model = os.getenv("CLAUSEAI_HIGH_QUALITY_MODEL", "llama-3.3-70b-versatile")

        max_retries = max(0, int(os.getenv("CLAUSEAI_GROQ_MAX_RETRIES", "5")))
        backoff_base = float(os.getenv("CLAUSEAI_GROQ_BACKOFF_BASE", "3.0"))
        last_err = None

        with _GROQ_REQUEST_LOCK:
            for attempt in range(max_retries + 1):
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": _llm_system_prompt()},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=_llm_temperature(),
                        max_tokens=num_predict,
                    )
                    return response.choices[0].message.content or ""
                except Exception as err:
                    last_err = err
                    if _is_rate_limit_error(err) and attempt < max_retries:
                        retry_after = _extract_retry_after_seconds(err)
                        sleep_s = retry_after if retry_after > 0 else backoff_base * (2 ** attempt)
                        sleep_s = min(60.0, max(1.0, sleep_s))
                        time.sleep(sleep_s)
                        continue
                    if _is_connection_error(err) and attempt < max_retries:
                        time.sleep(backoff_base * (attempt + 1))
                        continue
                    break

        if last_err:
            raise RuntimeError(
                f"High-quality Groq call failed after {max_retries+1} attempts. "
                f"Error: {str(last_err)[:200]}"
            ) from last_err
        return ""
    return get_llm_response(prompt, num_predict=num_predict)


# Return output as a stream so the caller can read chunks safely.
def get_llm_response_stream(prompt: str, num_predict: int = 600):
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
    from config.config import HF_EMBEDDING_MODEL, HF_TOKEN

    try:
        from sentence_transformers import SentenceTransformer
    except Exception:
        return None
    if HF_TOKEN:
        # Mirror the token into the environment so huggingface_hub and related
        # libraries can reuse it without extra setup.
        os.environ.setdefault("HF_TOKEN", HF_TOKEN)
        os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", HF_TOKEN)

    # This warning is a known harmless mismatch for many sentence-transformer
    # checkpoints and does not affect embedding quality here.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*embeddings\.position_ids.*UNEXPECTED.*",
        )
        return SentenceTransformer(HF_EMBEDDING_MODEL, token=HF_TOKEN)


def _hf_embedding_runtime_available() -> bool:
    from config.config import EMBEDDING_PROVIDER

    if EMBEDDING_PROVIDER != "hf":
        return False
    return importlib.util.find_spec("sentence_transformers") is not None


def _openai_embedding_runtime_available() -> bool:
    from config.config import EMBEDDING_PROVIDER, OPENAI_API_KEY

    if EMBEDDING_PROVIDER != "openai" or not OPENAI_API_KEY:
        return False
    return importlib.util.find_spec("openai") is not None


def _as_vector(raw_embedding: Any) -> List[float]:
    # Handles list, tuple, numpy array, and tensor-like outputs.
    if hasattr(raw_embedding, "tolist"):
        values = raw_embedding.tolist()
    else:
        values = raw_embedding
    return [float(v) for v in values]


_DOC_EMBED_INDEX: Dict[str, Dict[str, Any]] = {}
_DOC_EMBED_INDEX_LOCK = Lock()
_QUERY_CACHE: Dict[str, str] = {}
_QUERY_CACHE_LOCK = Lock()
_ARTIFACT_CACHE: Dict[str, Any] = {}
_ARTIFACT_CACHE_LOCK = Lock()
_TEXT_EMBED_CACHE: Dict[str, List[float]] = {}
_TEXT_EMBED_CACHE_LOCK = Lock()
_GROQ_REQUEST_LOCK = Lock()


def _embed_cache_limit() -> int:
    return max(64, int(os.getenv("CLAUSEAI_EMBED_CACHE_SIZE", "512")))


def _embed_cache_key(text: str) -> str:
    from config.config import EMBEDDING_MODEL, EMBEDDING_PROVIDER

    digest = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return f"{EMBEDDING_PROVIDER}::{EMBEDDING_MODEL}::{digest}"


def _pinecone_enabled() -> bool:
    from config.config import PINECONE_API_KEY, PINECONE_INDEX

    return bool(PINECONE_API_KEY and PINECONE_INDEX)


def _embedding_dimension() -> int:
    from config.config import EMBEDDING_MODEL, EMBEDDING_PROVIDER, OPENAI_API_KEY

    if EMBEDDING_PROVIDER == "openai" and OPENAI_API_KEY:
        known_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return known_dimensions.get(EMBEDDING_MODEL, 1536)

    embedder = _get_hf_embedder()
    if embedder is None:
        raise RuntimeError("No embedding provider available.")

    sample = embedder.encode(["dimension probe"], normalize_embeddings=True)
    return len(_as_vector(sample[0]))


@lru_cache(maxsize=1)
def _get_openai_client():
    from config.config import OPENAI_API_KEY

    if not OPENAI_API_KEY:
        return None
    from openai import OpenAI

    return OpenAI(api_key=OPENAI_API_KEY)


def _embed_with_hf(texts: List[str]) -> List[List[float]]:
    embedder = _get_hf_embedder()
    if embedder is None:
        raise RuntimeError("No local embedding provider available.")
    embeddings = embedder.encode(texts, normalize_embeddings=True)
    return [_as_vector(item) for item in embeddings]


def _embed_texts(texts: List[str]) -> List[List[float]]:
    payload = [text for text in texts if (text or "").strip()]
    if not payload:
        return []

    ordered_keys = [_embed_cache_key(text) for text in payload]
    cached_vectors: Dict[str, List[float]] = {}
    missing_by_key: Dict[str, str] = {}
    with _TEXT_EMBED_CACHE_LOCK:
        for key, text in zip(ordered_keys, payload):
            cached = _TEXT_EMBED_CACHE.get(key)
            if cached is not None:
                cached_vectors[key] = list(cached)
            elif key not in missing_by_key:
                missing_by_key[key] = text

    missing_items = list(missing_by_key.items())
    from config.config import EMBEDDING_PROVIDER

    if missing_items:
        missing_payload = [text for _, text in missing_items]
        client = _get_openai_client() if EMBEDDING_PROVIDER == "openai" else None
        if client is not None:
            from config.config import EMBEDDING_MODEL

            try:
                response = client.embeddings.create(model=EMBEDDING_MODEL, input=missing_payload)
                fresh_vectors = [[float(v) for v in item.embedding] for item in response.data]
            except Exception as err:
                if _is_insufficient_quota_error(err) or _is_rate_limit_error(err) or _is_connection_error(err):
                    try:
                        fresh_vectors = _embed_with_hf(missing_payload)
                    except Exception:
                        raise RuntimeError(
                            "Embedding generation failed with OpenAI and no local fallback is available."
                        ) from err
                else:
                    raise
        else:
            try:
                fresh_vectors = _embed_with_hf(missing_payload)
            except Exception as err:
                raise RuntimeError(
                    "No embedding provider available. Configure OPENAI_API_KEY or install sentence-transformers."
                ) from err

        with _TEXT_EMBED_CACHE_LOCK:
            for (key, _), vector in zip(missing_items, fresh_vectors):
                cached_vectors[key] = list(vector)
                _TEXT_EMBED_CACHE[key] = list(vector)
            while len(_TEXT_EMBED_CACHE) > _embed_cache_limit():
                oldest_key = next(iter(_TEXT_EMBED_CACHE))
                _TEXT_EMBED_CACHE.pop(oldest_key, None)

    return [list(cached_vectors[key]) for key in ordered_keys]


@lru_cache(maxsize=1)
def _get_pinecone_index():
    if not _pinecone_enabled():
        return None

    from config.config import PINECONE_API_KEY, PINECONE_CLOUD, PINECONE_HOST, PINECONE_INDEX, PINECONE_REGION

    from pinecone import Pinecone, ServerlessSpec

    client = Pinecone(api_key=PINECONE_API_KEY)
    if PINECONE_HOST:
        return client.Index(host=PINECONE_HOST)

    try:
        listed = client.list_indexes()
        if hasattr(listed, "names"):
            existing = set(listed.names())
        else:
            existing = {
                item["name"] if isinstance(item, dict) else getattr(item, "name", "")
                for item in listed
            }
            existing.discard("")
    except Exception:
        existing = set()

    if PINECONE_INDEX not in existing:
        client.create_index(
            name=PINECONE_INDEX,
            dimension=_embedding_dimension(),
            metric="cosine",
            spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
        )

    return client.Index(PINECONE_INDEX)


def _cache_key(query: str, doc_id: Optional[str], k: int) -> str:
    return f"{doc_id or 'none'}::{k}::{query.strip().lower()}"


def _artifact_record_id(cache_key: str) -> str:
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return f"artifact-{digest}"


@lru_cache(maxsize=1)
def _zero_vector() -> List[float]:
    return [0.0] * _embedding_dimension()


# Quick check to see if vector search is ready to use.
def vectorstore_available() -> bool:
    if _pinecone_enabled():
        try:
            return _get_pinecone_index() is not None
        except Exception:
            pass
    try:
        return _hf_embedding_runtime_available() or _openai_embedding_runtime_available()
    except Exception:
        return False


# Save contract chunks with doc info so we can search the right contract later.
def index_contract_chunks(chunks: List[str], doc_id: str) -> bool:
    cleaned_chunks = [chunk.strip() for chunk in chunks if (chunk or "").strip()]
    if not cleaned_chunks:
        return False

    with _DOC_EMBED_INDEX_LOCK:
        existing = _DOC_EMBED_INDEX.get(doc_id)
        if existing and existing.get("chunks") == cleaned_chunks:
            return True

    try:
        vectors = _embed_texts(cleaned_chunks)
    except Exception:
        return False

    if _pinecone_enabled():
        try:
            from config.config import PINECONE_NAMESPACE

            index = _get_pinecone_index()
            batch_size = max(8, int(os.getenv("CLAUSEAI_PINECONE_BATCH_SIZE", "32")))
            for start in range(0, len(cleaned_chunks), batch_size):
                end = start + batch_size
                batch = []
                for idx, (chunk, vector) in enumerate(zip(cleaned_chunks[start:end], vectors[start:end]), start=start):
                    batch.append(
                        {
                            "id": f"{doc_id}-{idx}",
                            "values": vector,
                            "metadata": {"doc_id": doc_id, "chunk_index": idx, "text": chunk},
                        }
                    )
                if batch:
                    index.upsert(vectors=batch, namespace=PINECONE_NAMESPACE)
        except Exception:
            # Fall back to the in-process index so analysis still completes.
            pass

    with _DOC_EMBED_INDEX_LOCK:
        _DOC_EMBED_INDEX[doc_id] = {"chunks": cleaned_chunks, "vectors": vectors}
    with _QUERY_CACHE_LOCK:
        stale_keys = [key for key in _QUERY_CACHE if key.startswith(f"{doc_id}::")]
        for key in stale_keys:
            _QUERY_CACHE.pop(key, None)
    return True


def retrieve_analysis_artifact(cache_key: str) -> Optional[Any]:
    key = (cache_key or "").strip()
    if not key:
        return None

    with _ARTIFACT_CACHE_LOCK:
        cached = _ARTIFACT_CACHE.get(key)
    if cached is not None:
        return cached

    if _pinecone_enabled():
        try:
            from config.config import PINECONE_NAMESPACE

            index = _get_pinecone_index()
            response = index.fetch(ids=[_artifact_record_id(key)], namespace=PINECONE_NAMESPACE)
            vectors = getattr(response, "vectors", None)
            if vectors is None and isinstance(response, dict):
                vectors = response.get("vectors", {})
            record = None
            if isinstance(vectors, dict):
                record = next(iter(vectors.values()), None)
            metadata = getattr(record, "metadata", None) or (record or {}).get("metadata", {})
            payload = (metadata or {}).get("payload")
            if payload:
                parsed = json.loads(payload)
                with _ARTIFACT_CACHE_LOCK:
                    _ARTIFACT_CACHE[key] = parsed
                return parsed
        except Exception:
            pass

    return None


def store_analysis_artifact(cache_key: str, payload: Any) -> bool:
    key = (cache_key or "").strip()
    if not key:
        return False

    try:
        encoded_payload = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return False

    with _ARTIFACT_CACHE_LOCK:
        _ARTIFACT_CACHE[key] = payload

    if _pinecone_enabled():
        try:
            from config.config import PINECONE_NAMESPACE

            index = _get_pinecone_index()
            index.upsert(
                vectors=[
                    {
                        "id": _artifact_record_id(key),
                        "values": _zero_vector(),
                        "metadata": {"record_type": "artifact", "cache_key": key, "payload": encoded_payload},
                    }
                ],
                namespace=PINECONE_NAMESPACE,
            )
        except Exception:
            pass

    return True


# Fetch most relevant saved chunks to give the agent better context.
def retrieve_context(query: str, doc_id: Optional[str] = None, k: int = 3) -> str:
    if not doc_id or not (query or "").strip():
        return ""

    cache_key = _cache_key(query, doc_id, k)
    with _QUERY_CACHE_LOCK:
        cached = _QUERY_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if _pinecone_enabled():
        try:
            from config.config import PINECONE_NAMESPACE

            index = _get_pinecone_index()
            query_vectors = _embed_texts([query])
            if not query_vectors:
                return ""
            query_vec = query_vectors[0]
            response = index.query(
                vector=query_vec,
                top_k=max(1, k),
                namespace=PINECONE_NAMESPACE,
                include_metadata=True,
                filter={"doc_id": {"$eq": doc_id}},
            )
            matches = getattr(response, "matches", None) or response.get("matches", [])
            top_chunks = []
            for match in matches:
                metadata = getattr(match, "metadata", None) or match.get("metadata", {})
                text = (metadata or {}).get("text", "").strip()
                if text:
                    top_chunks.append(text)
            if top_chunks:
                result = "\n\n".join(top_chunks)
                with _QUERY_CACHE_LOCK:
                    _QUERY_CACHE[cache_key] = result
                return result
        except Exception:
            pass

    with _DOC_EMBED_INDEX_LOCK:
        doc_record = _DOC_EMBED_INDEX.get(doc_id)
    if not doc_record:
        return ""

    try:
        query_vectors = _embed_texts([query])
    except Exception:
        return ""
    if not query_vectors:
        return ""
    query_vec = query_vectors[0]
    scored_chunks = []
    for idx, chunk_vec in enumerate(doc_record["vectors"]):
        score = sum(a * b for a, b in zip(query_vec, chunk_vec))
        scored_chunks.append((score, idx))
    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    result = "\n\n".join(doc_record["chunks"][idx] for _, idx in scored_chunks[: max(1, k)])
    with _QUERY_CACHE_LOCK:
        _QUERY_CACHE[cache_key] = result
    return result


# Run one specialist agent and return its findings.
def run_role_agent(
    role_name: str,
    contract_text: str,
    retrieved_context: str = "",
    num_predict: int = 500,
    peer_context: str = "",
    turn_number: int = 1,
    max_turns: int = 1,
    contract_type: str = "Auto-detect",
    evidence_signals: str = "",
    validated_extraction: str = "",
) -> str:
    role = ANALYST_ROLES[role_name]
    checks = "\n".join(f"- {item}" for item in role.checks)
    prompt = build_role_analysis_prompt(
        role_title=role.title,
        mission=role.mission,
        checks=checks,
        contract_text=contract_text,
        retrieved_context=retrieved_context,
        peer_context=peer_context,
        turn_number=turn_number,
        max_turns=max_turns,
        contract_type=contract_type,
        evidence_signals=evidence_signals,
        validated_extraction=validated_extraction,
    )
    return get_llm_response(prompt, num_predict=num_predict)

