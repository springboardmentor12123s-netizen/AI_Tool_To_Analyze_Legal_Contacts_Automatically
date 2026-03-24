# ClauseAI API Reference

All backend requests are routed through `src/api.py`.

### 1. `POST /upload_bulk`
- **Description**: Upload multiple contract documents (PDF, DOCX, TXT) to the server.
- **Body Expected**: `multipart/form-data` with a list of `files`.
- **Response**:
    ```json
    {
      "filenames": ["contract1.pdf", "contract2.docx"],
      "message": "Files uploaded successfully."
    }
    ```

### 2. `POST /analyze_bulk`
- **Description**: Triggers concurrent extraction and analysis on a list of uploaded documents.
- **Body Expected**: JSON (`AnalyzeBulkRequest`):
    ```json
    {
      "filenames": ["contract1.pdf", "contract2.docx"],
      "report_config": {
        "tone": "formal",
        "structure": ["summary", "risks"],
        "focus": ["liability"]
      }
    }
    ```
- **Response**: JSON array containing individual extraction states and generation output:
    ```json
    {
      "results": [
        {
          "filename": "contract1.pdf",
          "extracted_data": { ... },
          "final_report": "## Executive Summary...",
          "status": "success"
        }
      ]
    }
    ```

### 3. `POST /feedback`
- **Description**: Saves user feedback on generated reports.
- **Body Expected**: JSON (`FeedbackRequest`):
    ```json
    {
      "filename": "contract1.pdf",
      "section": "overall",
      "rating": "up",
      "comment": "Accurate findings."
    }
    ```
- **Response**:
    ```json
    {
      "status": "success",
      "message": "Feedback saved."
    }
    ```

### 4. `POST /chat` (RAG)
- **Description**: Conversational endpoint to chat directly with document sub-chunks via Pinecone vector search.
- **Body Expected**: JSON (`ChatRequest`):
    ```json
    {
      "query": "What are the payment terms?",
      "filename": "contract1.pdf"
    }
    ```
- **Response**:
    ```json
    {
      "answer": "The payment terms state Net 30 days...",
      "sources_used": true
    }
    ```
