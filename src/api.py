import os
import shutil
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
    report_config: Dict[str, Any] = None

class AnalyzeBulkRequest(BaseModel):
    filenames: List[str]
    report_config: Dict[str, Any] = None

class FeedbackRequest(BaseModel):
    filename: str
    section: str
    rating: str
    comment: str = None

class ChatRequest(BaseModel):
    query: str
    filename: str = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="ClauseAI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://10.11.224.104:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        if request.report_config:
            initial_state["report_config"] = request.report_config
        
        # Run Graph Asynchronously
        result = await agent_app.ainvoke(initial_state)
        
        response = {
            "extracted_data": result.get("extracted_data"),
            "final_report": result.get("final_report")
        }
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis Error: {str(e)}")

@app.post("/upload_bulk")
async def upload_bulk(files: List[UploadFile] = File(...)):
    """Upload multiple contracts."""
    saved_files = []
    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)
    return {"filenames": saved_files, "message": "Files uploaded successfully."}

@app.post("/analyze_bulk")
async def analyze_bulk(request: AnalyzeBulkRequest):
    """Analyze multiple uploaded contracts asynchronously."""
    from src.bulk_processor import process_all_documents
    file_paths = []
    for fname in request.filenames:
        fp = os.path.join(UPLOAD_DIR, fname)
        if not os.path.exists(fp):
            raise HTTPException(status_code=404, detail=f"File not found: {fname}")
        file_paths.append(fp)
    
    try:
        results = await process_all_documents(file_paths, config=request.report_config)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk Analysis Error: {str(e)}")

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Save user feedback on a report section."""
    feedback_file = "data/feedback.jsonl"
    os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
    with open(feedback_file, "a") as f:
        f.write(request.model_dump_json() + "\n")
    return {"status": "success", "message": "Feedback saved."}

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
