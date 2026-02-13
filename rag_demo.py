import os
from dotenv import load_dotenv
import certifi

from sentence_transformers import SentenceTransformer
from pymongo import MongoClient
from groq import Groq

# 1. Load env
load_dotenv()

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MONGODB_URI = os.environ["MONGODB_URI"]
DB_NAME = os.environ.get("MONGODB_DB", "rag_db")
COLL_NAME = os.environ.get("MONGODB_COLLECTION", "documents")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# 2. Init services
print("Loading embedding model...")
embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
EMBED_DIM = embed_model.get_sentence_embedding_dimension()
print(f"Embedding model: {EMBEDDING_MODEL_NAME}, dim={EMBED_DIM}")

print("Connecting to MongoDB...")
# specific fix for macOS SSL errors
mongo_client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
db = mongo_client[DB_NAME]
coll = db[COLL_NAME]
print("Connected to MongoDB.")

print("Initializing Groq client...")
groq_client = Groq(api_key=GROQ_API_KEY)
print("Groq client ready.\n")


def embed(text: str):
    return embed_model.encode(text, normalize_embeddings=True).tolist()


def ingest_sample_docs():
    docs = [
        {
            "text": "Groq is a company that provides ultra-fast inference for large language models using LPUs.",
            "metadata": {"source": "groq", "topic": "infrastructure"},
        },
        {
            "text": "MongoDB Atlas supports vector search, allowing you to store embeddings and run similarity queries.",
            "metadata": {"source": "mongodb", "topic": "database"},
        },
        {
            "text": "Retrieval-Augmented Generation, or RAG, retrieves relevant documents and feeds them to an LLM to answer questions.",
            "metadata": {"source": "rag", "topic": "ai"},
        },
    ]

    print("Generating embeddings and inserting sample docs...")
    for d in docs:
        emb = embed(d["text"])
        d["embedding"] = emb
        coll.insert_one(d)
    print("Sample docs ingested.\n")


def vector_search(query: str, k: int = 3):
    q_emb = embed(query)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",        # must match Atlas index name
                "path": "embedding",
                "queryVector": q_emb,
                "numCandidates": k * 10,
                "limit": k,
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    results = list(coll.aggregate(pipeline))
    return results


def ask_groq(question: str, context: str) -> str:
    system_prompt = (
        "You are a helpful assistant. Answer strictly using the given context. "
        "If the context is not enough, say you don't know."
    )

    user_message = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return resp.choices[0].message.content


def run_demo():
    # 1. Ingest small sample if collection is empty
    if coll.count_documents({}) == 0:
        ingest_sample_docs()
    else:
        print(f"Collection already has {coll.count_documents({})} docs, skipping ingest.\n")

    # 2. Query
    question = "What is RAG and how does Groq fit in?"
    print(f"Question: {question}\n")

    hits = vector_search(question, k=3)
    if not hits:
        print("No results from vector search. Check your Atlas vector index.")
        return

    print("Top retrieved chunks:")
    for h in hits:
        print(f"- score={h['score']:.4f}, source={h['metadata'].get('source')}")
        print(f"  text: {h['text'][:100]}...\n")

    # 3. Build context
    context = "\n\n".join(f"[{i+1}] {h['text']}" for i, h in enumerate(hits))

    # 4. Ask Groq
    answer = ask_groq(question, context)
    print("\n=== Answer from Groq ===\n")
    print(answer)


if __name__ == "__main__":
    run_demo()
