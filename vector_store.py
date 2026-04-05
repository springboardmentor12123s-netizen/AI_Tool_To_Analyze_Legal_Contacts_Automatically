import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# ---------------------------
# LOAD ENV VARIABLES
# ---------------------------
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("❌ Missing Pinecone API Key in .env")

# ---------------------------
# INIT PINECONE (CORRECT WAY)
# ---------------------------
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "clauseai"   # 👈 your index name

try:
    index = pc.Index(INDEX_NAME)
    print("✅ Connected to Pinecone Index:", INDEX_NAME)
except Exception as e:
    print("❌ Pinecone Connection Error:", e)

# ---------------------------
# EMBEDDING MODEL
# ---------------------------
model = SentenceTransformer("all-MiniLM-L6-v2")

# ---------------------------
# STORE DATA
# ---------------------------
def store_data(id, text):
    try:
        embedding = model.encode(text).tolist()

        index.upsert([
            {
                "id": id,
                "values": embedding,
                "metadata": {"text": text}
            }
        ])

        print(f"✅ Stored: {id}")

    except Exception as e:
        print("❌ Store Error:", e)


# ---------------------------
# RETRIEVE SIMILAR
# ---------------------------
def retrieve_similar(query_text, top_k=3):
    try:
        query_embedding = model.encode(query_text).tolist()

        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )

        matches = results.get("matches", [])

        retrieved_texts = [
            match["metadata"]["text"]
            for match in matches
            if "metadata" in match and "text" in match["metadata"]
        ]

        print("✅ Retrieved:", len(retrieved_texts))

        return retrieved_texts

    except Exception as e:
        print("❌ Retrieval Error:", e)
        return []
