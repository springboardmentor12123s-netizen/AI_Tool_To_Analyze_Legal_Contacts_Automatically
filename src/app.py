import streamlit as st
from graph import contract_graph
from pypdf import PdfReader

# Pinecone imports
import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer


# ---------------- LOAD ENV ----------------

load_dotenv()


# ---------------- PINECONE SETUP ----------------

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = "contract-index"

index = pc.Index(index_name)

# embedding model (384 dimension)
model = SentenceTransformer("all-MiniLM-L6-v2")


# ---------------- STORE RESULTS FUNCTION ----------------

def store_results(result):

    vectors = [
        {
            "id": "compliance",
            "values": model.encode(result["compliance_result"]).tolist(),
            "metadata": {"text": result["compliance_result"]}
        },
        {
            "id": "legal",
            "values": model.encode(result["legal_result"]).tolist(),
            "metadata": {"text": result["legal_result"]}
        },
        {
            "id": "finance",
            "values": model.encode(result["finance_result"]).tolist(),
            "metadata": {"text": result["finance_result"]}
        },
        {
            "id": "operations",
            "values": model.encode(result["operations_result"]).tolist(),
            "metadata": {"text": result["operations_result"]}
        }
    ]

    index.upsert(vectors)


# ---------------- PDF TEXT EXTRACTION ----------------

def extract_text_from_pdf(uploaded_file):

    reader = PdfReader(uploaded_file)

    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return text


# ---------------- STREAMLIT UI ----------------

st.title("AI Contract Risk Analyzer")

uploaded_file = st.file_uploader("Upload Contract PDF", type=["pdf"])


if uploaded_file is not None:

    contract_text = extract_text_from_pdf(uploaded_file)

    if st.button("Analyze Contract"):

        with st.spinner("Analyzing contract..."):

            # limit size to avoid token limit
            MAX_CHARS = 4000
            contract_text = contract_text[:MAX_CHARS]

            result = contract_graph.invoke({
                "contract": contract_text
            })

            # ---- STORE INTERMEDIATE RESULTS IN PINECONE ----
            store_results(result)

        st.success("Analysis Complete!")

        st.header("Risk Analysis Results")

        st.subheader("Compliance Analysis")
        st.text(result["compliance_result"])

        st.subheader("Legal Analysis")
        st.text(result["legal_result"])

        st.subheader("Finance Analysis")
        st.text(result["finance_result"])

        st.subheader("Operations Analysis")
        st.text(result["operations_result"])