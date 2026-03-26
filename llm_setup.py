from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

# Use same stable model for both
planning_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2
)

analysis_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3
)