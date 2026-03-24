import asyncio
import os

from src.bulk_processor import process_all_documents

async def main():
    print("="*50)
    print("🚀 Running Concurrent Pipeline Verification on Multiple Documents")
    print("="*50)
    
    # Selecting the sample documents available in the directory
    sample_files = ["test.docx", "contract.pdf", "contract_claude.docx"]
    valid_files = [f for f in sample_files if os.path.exists(f)]
    
    if not valid_files:
        print("Error: Could not find any test documents in the current directory.")
        return

    config = {
        "tone": "executive",
        "structure": ["summary", "risks", "recommendations"],
        "focus": ["liability", "payment_terms"]
    }
    
    print(f"\n[1] Found {len(valid_files)} documents to analyze concurrently: {', '.join(valid_files)}")
    print(f"  - Configuration used: Tone={config['tone']}, Focus={config['focus']}")
    
    print("\n[2] Executing Bulk Processor (Concurrent Extraction & Report Generation)......")
    
    results = await process_all_documents(valid_files, config=config)
    
    print("-" * 50)
    success_count = 0
    for res in results:
        status = res.get("status")
        filename = res.get("filename")
        if status == "success":
            success_count += 1
            print(f"✅ Document: {filename} processed successfully!")
            # Truncating report print out to keep the terminal output readable
            report_lines = res.get("final_report", "").split("\n")
            preview = "\n".join(report_lines[:5]) + "\n... (omitted remainder of report) ..."
            print(f"--- Preview for {filename} ---\n{preview}\n")
        else:
            print(f"❌ Error processing {filename}: {res.get('error')}")
            
    print("="*50)
    print(f"✅ Async Pipeline processed {success_count}/{len(valid_files)} documents successfully!")

if __name__ == "__main__":
    asyncio.run(main())
