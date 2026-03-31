from dotenv import load_dotenv
from modules.clients import get_clients
import streamlit as st

load_dotenv()

# Load cached Gemini + Pinecone clients
client, pc = get_clients()


@st.cache_data
def get_embedding(text):
    
    response = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text
    )

    return response.embeddings[0].values