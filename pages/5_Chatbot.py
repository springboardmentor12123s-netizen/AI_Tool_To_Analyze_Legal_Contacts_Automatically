import streamlit as st
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.helpers import inject_custom_css
from src.config import get_llm, get_embeddings, Config
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from pinecone import Pinecone

st.set_page_config(page_title="AI Chatbot", layout="wide", page_icon="🤖")
inject_custom_css()

st.title("🤖 Ask the Contract")
st.caption("Chat directly with the AI about your uploaded portfolio.")

# --- CHECK DATA ---
if "analysis_results" not in st.session_state or not st.session_state.analysis_results:
    st.warning("No contracts analyzed yet. Please go to the Upload page.")
    st.stop()

# --- INITIALIZE CHAT ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- DISPLAY CHAT ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- USER INPUT ---
user_query = st.chat_input("Ask a question about the contracts...")

if user_query:
    # Add user msg
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # --- RETRIEVAL ---
    with st.chat_message("assistant"):
        with st.spinner("Searching pinecone vector database..."):

            try:
                # Setup Retrieval
                pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
                index = pc.Index(Config.PINECONE_INDEX_NAME)

                embeddings = get_embeddings()

                query_vec = embeddings.embed_query(user_query)

                res = index.query(
                    vector=query_vec,
                    top_k=5,
                    include_metadata=True,
                    namespace="default"
                )

                context = "\n".join([match['metadata'].get('text', '') for match in res.get('matches', [])])

                # Generation
                llm = get_llm()

                prompt = ChatPromptTemplate.from_template(
                    """You are a specialized Legal/Financial Assistant analyzing a contract.
                    
                    Answer the user's question based ONLY on the provided context retrieved from the contract.
                    If the answer isn't firmly stated in the context, say "I don't have enough context from the contract to answer this."
                    
                    CONTEXT:
                    {context}
                    
                    USER QUESTION:
                    {question}
                    """
                )

                chain = prompt | llm | StrOutputParser()

                response = chain.invoke({
                    "context": context,
                    "question": user_query
                })

                st.markdown(response)

                with st.expander("Show Retrieved Context"):
                    st.write(context)

                # Save response
                st.session_state.chat_history.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"Error communicating with AI/VectorDB: {str(e)}"
                st.error(error_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})

if st.button("🗑️ Clear Chat"):
    st.session_state.chat_history = []
    st.rerun()