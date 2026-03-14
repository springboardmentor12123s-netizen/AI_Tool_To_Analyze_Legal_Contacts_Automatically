import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

load_dotenv()

# Load embedding model
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Pinecone setup
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "contract-index"

if INDEX_NAME not in [i.name for i in pc.list_indexes()]:
    pc.create_index(
        name=INDEX_NAME,
        dimension=384,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

index = pc.Index(INDEX_NAME)


def store_document(text):
    chunks = [text[i:i+500] for i in range(0, len(text), 500)]
    
    vectors = []
    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk).tolist()
        vectors.append((f"id_{i}", embedding, {"text": chunk}))
    
    index.upsert(vectors)


def retrieve_context(query):
    query_embedding = model.encode(query).tolist()
    
    results = index.query(
        vector=query_embedding,
        top_k=3,
        include_metadata=True
    )
    
    retrieved = ""
    for match in results["matches"]:
        retrieved += match["metadata"]["text"] + "\n\n"
    
    return retrieved