from pinecone import Pinecone
from modules.embeddings import get_embedding
from dotenv import load_dotenv
import time
import os
import uuid

load_dotenv()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# Use your actual host
index = pc.Index(
    host="contract-isq03et.svc.aped-4627-b74a.pinecone.io"
)

# -----------------------------------------
# STORE CHUNKS (UPDATED)
# -----------------------------------------
def store_chunks(chunks, namespace):

    vectors = []

    for i, chunk in enumerate(chunks):

        embedding = get_embedding(chunk)

        vectors.append({
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {"text": chunk}
        })

        # 🔥 Delay to avoid rate limit
        time.sleep(0.3)

        # 🔥 Batch upsert every 20 chunks (better performance)
        if len(vectors) >= 20:
            index.upsert(
                vectors=vectors,
                namespace=namespace
            )
            vectors = []

    # 🔥 Final remaining vectors
    if vectors:
        index.upsert(
            vectors=vectors,
            namespace=namespace
        )


# -----------------------------------------
# RETRIEVE RELEVANT CHUNKS
# -----------------------------------------
def retrieve_chunks(query, namespace, top_k=3):

    query_embedding = get_embedding(query)

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace
    )

    return [match["metadata"]["text"] for match in results["matches"]]