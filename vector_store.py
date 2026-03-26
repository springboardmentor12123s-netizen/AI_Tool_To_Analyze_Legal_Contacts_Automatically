from pinecone import Pinecone
import os

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("clauseai")

def store_data(id, text):
    index.upsert([
        {
            "id": id,
            "values": [0.1]*1536,
            "metadata": {"text": text}
        }
    ])