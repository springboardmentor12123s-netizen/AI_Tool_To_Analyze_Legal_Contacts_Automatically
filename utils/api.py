import os
import sys
import tempfile
import re

# Add root folder to sys path so we can import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.document_utils import extract_text_from_pdf, create_documents_from_text
from src.pinecone_utils import PineconeManager
from src.clause_ai_graph import ClauseAIGraph
from utils.helpers import extract_json_metrics

def process_contract_stream(uploaded_file, file_bytes, tone, structure, focus):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        raw_text = extract_text_from_pdf(tmp_path)
        if not raw_text.strip():
            return {"error": "No text extracted.", "file": uploaded_file.name}
            
        docs = create_documents_from_text(raw_text, uploaded_file.name)
        PineconeManager().add_documents(docs)
        
        # Execute workflow
        graph = ClauseAIGraph()
        query = "Perform a full multi-domain audit of this contract for risks and obligations."
        final_state = graph.run(query, tone=tone, structure=structure, focus=focus, source_file=uploaded_file.name)
        
        result = final_state
        result["file"] = uploaded_file.name
        result["raw_text"] = raw_text
        
        metrics = extract_json_metrics(result.get("final_report", ""))
        if metrics:
            result["metrics"] = metrics
            # Remove json block from final report text
            result["final_report"] = re.sub(r'```json.*?```', '', result["final_report"], flags=re.DOTALL).strip()
            
        return result
    except Exception as e:
        return {"error": str(e), "file": uploaded_file.name}
    finally:
        try: os.remove(tmp_path)
        except: pass
