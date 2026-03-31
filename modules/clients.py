from google import genai
from pinecone import Pinecone
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

@st.cache_resource
def get_clients():

    gemini_client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options={"api_version": "v1beta"}
    )

    pinecone_client = Pinecone(
        api_key=os.getenv("PINECONE_API_KEY")
    )

    return gemini_client, pinecone_client