import hashlib
import os

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


# ----------------------------------------
# 🔑 Generate Cache Key
# ----------------------------------------

def generate_cache_key(text: str, tone: str, focus: str) -> str:
    raw = f"{text}_{tone}_{focus}"
    return hashlib.md5(raw.encode()).hexdigest()


# ----------------------------------------
# 📄 REPORT CACHE
# ----------------------------------------

def get_cached_report(key: str):
    path = os.path.join(CACHE_DIR, f"{key}.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def save_cached_report(key: str, content: str):
    path = os.path.join(CACHE_DIR, f"{key}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ----------------------------------------
# 📄 PDF CACHE
# ----------------------------------------

def get_cached_pdf(key: str):
    path = os.path.join(CACHE_DIR, f"{key}.pdf")
    return path if os.path.exists(path) else None


def save_cached_pdf(key: str, pdf_path: str):
    cache_path = os.path.join(CACHE_DIR, f"{key}.pdf")

    with open(pdf_path, "rb") as src, open(cache_path, "wb") as dst:
        dst.write(src.read())

    return cache_path
# ----------------------------------------
# 💬 Q&A CACHE (NEW)
# ----------------------------------------

def generate_qa_cache_key(question: str, contract_id: str) -> str:
    raw = f"{question}_{contract_id}"
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached_qa(key: str):
    path = os.path.join(CACHE_DIR, f"{key}_qa.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return None


def save_cached_qa(key: str, answer: str):
    path = os.path.join(CACHE_DIR, f"{key}_qa.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(answer)