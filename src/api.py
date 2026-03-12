import os
import shutil
from typing import List, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

from src.ingest import load_document
from src.agent_graph import app as agent_app

# Create upload directory
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class AnalyzeRequest(BaseModel):
    filename: str

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
            "final_report": ""
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

if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
