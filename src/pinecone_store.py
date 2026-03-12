import os
import uuid
from typing import List, Dict, Any
from dotenv import load_dotenv

from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

class ContractVectorStore:
    def __init__(self, index_name="clauseai"):
        self.api_key = os.environ.get("PINECONE_API_KEY")
        self.index_name = index_name
        self.pc = Pinecone(api_key=self.api_key)
        
        # Initialize Embedder (Using sentence-transformers directly via Langchain wrapper)
        self.embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        self._ensure_index_exists()
        self.index = self.pc.Index(self.index_name)

    def _ensure_index_exists(self):
        existing_indexes = self.pc.list_indexes().names()
        if self.index_name not in existing_indexes:
            print(f"[PineconeStore] Creating index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=384, # matches all-MiniLM-L6-v2
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )

    def store_clause(self, clause_text: str, metadata: Dict[str, Any]):
        """Store an extracted/analyzed clause with its analysis metadata."""
        clause_id = str(uuid.uuid4())
        
        # Use Langchain wrapper to embed the query
        vector = self.embeddings_model.embed_query(clause_text)
        
        # Merge text into metadata for retrieval
        full_metadata = {
            "text": clause_text,
            "domain": metadata.get("domain", "unknown"),
            "risk_level": metadata.get("risk_level", "unknown"),
            "contract_id": metadata.get("contract_id", "unknown")
        }
        
        # Pinecone upsert
        self.index.upsert(vectors=[(clause_id, vector, full_metadata)])
        print(f"[PineconeStore] Stored clause {clause_id} for domain {full_metadata['domain']}")

    def retrieve_similar(self, query: str, domain_filter: str = None, contract_id: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve similar clauses, optionally filtered by domain and/or contract ID."""
        query_vector = self.embeddings_model.embed_query(query)
        
        filter_dict = {}
        if domain_filter:
            filter_dict["domain"] = domain_filter
        if contract_id:
            filter_dict["contract_id"] = contract_id
            
        results = self.index.query(
            vector=query_vector,
            top_k=top_k,
            filter=filter_dict,
            include_metadata=True
        )
        
        # Format results
        retrieved_clauses = []
        for match in results.get("matches", []):
            retrieved_clauses.append({
                "id": match["id"],
                "score": match["score"],
                "metadata": match["metadata"]
            })
            
        return retrieved_clauses

# Global instance for easy import if needed
vector_store_manager = ContractVectorStore()
