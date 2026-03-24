import os
import tempfile
import json
import hashlib
import asyncio
from asyncio import Semaphore
from typing import List, Dict, Any, Optional

from src.ingest import load_document
from src.agent_graph import app as agent_app

MAX_CONCURRENT = 5
CACHE_DIR = "data/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

class DocumentCache:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = cache_dir

    def _get_cache_path(self, hash_key: str) -> str:
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    async def get(self, hash_key: str) -> Optional[Dict[str, Any]]:
        path = self._get_cache_path(hash_key)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    async def set(self, hash_key: str, result: Dict[str, Any]):
        path = self._get_cache_path(hash_key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f)

cache = DocumentCache()

def compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

async def process_single(filename: str, file_path: str, sem: Semaphore, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    async with sem:
        try:
            # Load document text
            docs = load_document(file_path)
            full_text = "\n\n".join([d.page_content for d in docs])
            
            # Compute hash to check cache
            doc_hash = compute_hash(full_text)
            
            # Modify hash with config to ensure different configs yield different cache entries if needed
            # Actually, config only changes the report synthesis. The extraction takes the bulk of time.
            # Let's cache the full state or just the extracted data.
            # To simplify, we cache the whole result based on doc_hash + config hash.
            config_hash = compute_hash(json.dumps(config, sort_keys=True)) if config else "default"
            cache_key = f"{doc_hash}_{config_hash}"
            
            cached_result = await cache.get(cache_key)
            if cached_result:
                print(f"Cache hit for {filename}")
                return cached_result
                
            print(f"Analyzing {filename}...")
            # Initial State
            initial_state = {
                "contract_text": full_text,
                "clauses": [],
                "extracted_data": {},
                "final_report": "",
                "filename": filename
            }
            if config:
                initial_state["report_config"] = config
            
            # Run Graph Asynchronously
            result = await agent_app.ainvoke(initial_state)
            
            response = {
                "filename": filename,
                "extracted_data": result.get("extracted_data"),
                "final_report": result.get("final_report"),
                "status": "success"
            }
            
            await cache.set(cache_key, response)
            return response
            
        except Exception as e:
            return {
                "filename": filename,
                "status": "error",
                "error": str(e)
            }

async def process_all_documents(file_paths: List[str], config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Process multiple documents concurrently."""
    sem = Semaphore(MAX_CONCURRENT)
    
    tasks = []
    for fp in file_paths:
        filename = os.path.basename(fp)
        tasks.append(process_single(filename, fp, sem, config))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter exceptions into error responses
    processed_results = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            processed_results.append({
                "filename": os.path.basename(file_paths[i]),
                "status": "error",
                "error": str(r)
            })
        else:
            processed_results.append(r)
            
    return processed_results
