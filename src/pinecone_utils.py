from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.config import Config, get_pinecone_index

class PineconeManager:
    def __init__(self):
        """
        Initializes the manager with stable Gemini embeddings and the Pinecone index.
        Note: We force the API version to 'v1' to prevent the 404 Beta error.
        """
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            version="v1"  # Explicitly use stable v1 to avoid v1beta 404s
        )
        self.index = get_pinecone_index()

    def add_documents(self, documents, namespace="default"):
        vectors_to_upsert = []
        for i, doc in enumerate(documents):
            # We add the task_type and output_dimensionality to match your index
            embedding = self.embeddings.embed_query(
                doc.page_content,
                task_type="retrieval_document",
                output_dimensionality=768  # <--- THIS IS THE FIX
            )
            
            vectors_to_upsert.append({
                "id": f"doc_{i}_{hash(doc.page_content) % 10000}",
                "values": embedding,
                "metadata": {
                    "text": doc.page_content, 
                    "source": doc.metadata.get("source", "unknown")
                }
            })
        
        self.index.upsert(vectors=vectors_to_upsert, namespace=namespace)
        print(f"✅ Added {len(vectors_to_upsert)} chunks to Pinecone!")