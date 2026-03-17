import os
from dotenv import load_dotenv
from pinecone import Pinecone
from google import genai

# Load environment variables
load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not found in .env")

if not PINECONE_INDEX_NAME:
    raise ValueError("PINECONE_INDEX_NAME not found in .env")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")


# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)

# Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


# -----------------------------------------
# Generate embedding
# -----------------------------------------
def generate_embedding(text: str):

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    return response.embeddings[0].values


# -----------------------------------------
# Store document chunks
# -----------------------------------------
def store_chunks(chunks, namespace="contracts"):

    vectors = []

    for i, chunk in enumerate(chunks):

        embedding = generate_embedding(chunk)

        vectors.append({
            "id": f"chunk-{i}",
            "values": embedding,
            "metadata": {"text": chunk}
        })

    index.upsert(vectors=vectors, namespace=namespace)


# -----------------------------------------
# Retrieve clauses for agents
# -----------------------------------------
def retrieve_clauses(query, namespace="contracts", top_k=3):

    query_embedding = generate_embedding(query)

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True
    )

    clauses = []

    for match in results.matches:
        clauses.append(match.metadata["text"])

    return clauses


# -----------------------------------------
# Store agent analysis results (Milestone 3)
# -----------------------------------------
def store_agent_results(agent_name, results, namespace="agent-results"):

    text = str(results)

    embedding = generate_embedding(text)

    vector = {
        "id": f"{agent_name}-result",
        "values": embedding,
        "metadata": {
            "agent": agent_name,
            "analysis": text
        }
    }

    index.upsert(vectors=[vector], namespace=namespace)