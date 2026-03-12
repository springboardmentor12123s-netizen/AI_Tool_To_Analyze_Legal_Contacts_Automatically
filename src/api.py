import os
import shutil
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate

from src.ingest import load_document
from src.agent_graph import app as agent_app
from src.pinecone_store import vector_store_manager

# Create upload directory
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class AnalyzeRequest(BaseModel):
    filename: str

class ChatRequest(BaseModel):
    query: str
    filename: str = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="ClauseAI API", lifespan=lifespan)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a contract and save it."""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # We no longer ingest immediately. Ingestion/Extraction happens in the Graph.
        return {"filename": file.filename, "message": "File uploaded successfully."}
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_contract(request: AnalyzeRequest):
    """Analyze an uploaded contract using the Parallel Extraction AI Graph."""
    file_path = os.path.join(UPLOAD_DIR, request.filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Load document text
        docs = load_document(file_path)
        full_text = "\n\n".join([d.page_content for d in docs])
        
        # Initial State
        initial_state = {
            "contract_text": full_text,
            "clauses": [],
            "extracted_data": {},
            "final_report": "",
            "filename": request.filename
        }
        
        # Run Graph Asynchronously
        result = await agent_app.ainvoke(initial_state)
        
        response = {
            "extracted_data": result.get("extracted_data"),
            "final_report": result.get("final_report")
        }
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Error: {str(e)}")

@app.post("/chat")
async def chat_with_contract(request: ChatRequest):
    """Chat with the document using RAG and Groq fallback."""
    try:
        query = request.query
        filename = request.filename
        
        # 1. Retrieve context from Pinecone
        # Passing filename as contract_id if available to scope the search
        retrieved_docs = vector_store_manager.retrieve_similar(
            query=query, 
            contract_id=filename,
            top_k=4
        )
        
        context_text = ""
        if retrieved_docs:
            context_text = "\n\n".join([f"Clause: {doc['metadata']['text']}" for doc in retrieved_docs])
            
        # 2. Setup LLM and Prompt
        llm = ChatGroq(
            temperature=0, 
            model_name="llama-3.3-70b-versatile",
            api_key=os.environ.get("GROQ_API_KEY")
        )
        
        prompt_template = PromptTemplate.from_template('''
        You are ClauseAI, an expert legal and contract analysis assistant.
        A user has asked a question about a document. 
        
        Here is the relevant context extracted from the document:
        ---
        {context}
        ---
        
        User Question: {query}
        
        Instructions:
        1. If the user is just saying hello or asking for help, respond naturally and politely as ClauseAI without mentioning the document context.
        2. If the user's question can be answered clearly using the context above, do so completely and concisely.
        3. If the user's question is about the document but the context doesn't contain the answer, state that the document does not appear to contain this specific information.
        4. Even if the document doesn't contain the answer, do your best to provide a helpful, general response to their question using your broader knowledge.
        
        Answer:
        ''')
        
        chain = prompt_template | llm
        
        # 3. Generate response
        response = await chain.ainvoke({"context": context_text, "query": query})
        
        return {
            "answer": response.content,
            "sources_used": len(retrieved_docs) > 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
