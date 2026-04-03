import os
import sys
from dotenv import load_dotenv

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent_graph import app
from src.ingest import ingest_documents

load_dotenv()

TEST_CONTRACT = """
SERVICE AGREEMENT

1. Services. Provider agrees to deliver software development services including frontend and backend implementation.
2. Payment. Client agrees to pay $50,000 USD within 30 days of invoice. Late payments incur 5% interest per month.
3. Liability. Provider's total liability shall not exceed the total amount paid by Client.
4. Termination. Either party may terminate with 30 days written notice.
5. Law. This agreement is governed by the laws of California.
6. Compliance. Provider warrants that all code adheres to GDPR and CCPA regulations.
"""

def run_experiment():
    print("Starting Experiment with RAG...")
    
    # 1. Save contract to file for ingestion
    sample_file = "sample_contract.txt"
    with open(sample_file, "w") as f:
        f.write(TEST_CONTRACT)
        
    # 2. Ingest into Pinecone
    print(f"Ingesting {sample_file}...")
    ingest_documents([sample_file])
    
    # 3. Run the graph
    # Note: We don't strictly need to pass 'contract_text' anymore if using RAG,
    # but keeping it in state might be useful for reference or hybrid search.
    initial_state = {
        "contract_text": TEST_CONTRACT, 
        "compliance_analysis": "",
        "finance_analysis": "",
        "legal_analysis": "",
        "operations_analysis": ""
    }
    
    # Run the graph
    print("Invoking agent graph...")
    result = app.invoke(initial_state)
    
    print("\n\n=== EXPERIMENT RESULTS ===\n")
    
    print(">> COMPLIANCE ANALYSIS:")
    print(result.get("compliance_analysis", "No output"))
    print("-" * 50)
    
    print(">> FINANCE ANALYSIS:")
    print(result.get("finance_analysis", "No output"))
    print("-" * 50)
    
    print(">> LEGAL ANALYSIS:")
    print(result.get("legal_analysis", "No output"))
    print("-" * 50)
    
    print(">> OPERATIONS ANALYSIS:")
    print(result.get("operations_analysis", "No output"))
    print("-" * 50)
    
    # Cleanup
    if os.path.exists(sample_file):
        os.remove(sample_file)

if __name__ == "__main__":
    run_experiment()
