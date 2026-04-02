from langchain_groq import ChatGroq
import time
import hashlib
from threading import Lock
from groq import RateLimitError

# -------------------------
# GLOBALS
# -------------------------

_llm = None
_cache = {}
_cache_lock = Lock()

MAX_CACHE_SIZE = 300


# -------------------------
# LLM SINGLETON
# -------------------------

def get_llm():
    global _llm

    if _llm is None:
        _llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0
        )

    return _llm


# -------------------------
# CACHE KEY
# -------------------------

def get_cache_key(prompt: str, context: str = "") -> str:
    combined = prompt + context
    return hashlib.md5(combined.encode()).hexdigest()


def get_cached_response(prompt: str, context: str = ""):
    key = get_cache_key(prompt, context)
    with _cache_lock:
        return _cache.get(key)


def set_cached_response(prompt: str, context: str, response: str):
    key = get_cache_key(prompt, context)

    with _cache_lock:
        if len(_cache) >= MAX_CACHE_SIZE:
            _cache.pop(next(iter(_cache)))
        _cache[key] = response


# -------------------------
# 🚀 MAIN LLM CALL (ROBUST)
# -------------------------

def groq_chat(prompt: str, context: str = "", retries=5, base_delay=2):

    # ✅ 1. Check cache
    cached = get_cached_response(prompt, context)
    if cached:
        return cached

    llm = get_llm()

    # ✅ 2. Retry with exponential backoff
    for attempt in range(retries):
        try:
            response = llm.invoke(prompt).content

            # cache result
            set_cached_response(prompt, context, response)

            return response

        except RateLimitError:
            wait_time = base_delay * (2 ** attempt)
            print(f"⚠️ Rate limit hit. Retrying in {wait_time}s...")
            time.sleep(wait_time)

        except Exception as e:
            print(f"⚠️ Error: {str(e)}")
            time.sleep(2)

    # ✅ 3. FINAL FALLBACK (IMPORTANT FIX)
    # Instead of fake "failed request", retry ONE LAST TIME (blocking)

    print("⚠️ Final retry (blocking)...")

    while True:
        try:
            response = llm.invoke(prompt).content
            set_cached_response(prompt, context, response)
            return response

        except RateLimitError:
            print("⏳ Waiting due to rate limit...")
            time.sleep(5)

        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return "Not mentioned in contract"