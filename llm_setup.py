from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

load_dotenv()

# Gemini → Planning + Finance
# llm_setup.py
gemini_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",   # ✅ most generous free tier
    temperature=0.3,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Groq → Legal + Compliance
groq_llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.3,
    groq_api_key=os.getenv("GROQ_API_KEY")
)

planning_llm = gemini_llm
analysis_llm = gemini_llm

print("GEMINI KEY:", os.getenv("GOOGLE_API_KEY"))
print("GROQ KEY:", os.getenv("GROQ_API_KEY"))
