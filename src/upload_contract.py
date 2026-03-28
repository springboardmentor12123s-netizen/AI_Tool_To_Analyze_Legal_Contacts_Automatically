import sys
import os

from src.document_utils import extract_text_from_pdf, create_documents_from_text
from src.pinecone_utils import PineconeManager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def verify_and_upload(file_path: str):
    print(f"🔍 Starting Verification for: {file_path}")
    
    
    raw_text = extract_text_from_pdf(file_path)
    
    if not raw_text.strip():
        print("❌ FAILED: No text extracted. Check if PDF is scanned/image-only.")
        return

    print("Step 2: Creating document chunks...")
    docs = create_documents_from_text(raw_text, os.path.basename(file_path))
    
    print(f"Step 3: Uploading {len(docs)} chunks to Pinecone...")
    manager = PineconeManager()
    manager.add_documents(docs)
    print("✅ Successfully uploaded to Pinecone.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        verify_and_upload(sys.argv[1])
    else:
        print("Usage: python -m src.upload_contract <filename.pdf>")