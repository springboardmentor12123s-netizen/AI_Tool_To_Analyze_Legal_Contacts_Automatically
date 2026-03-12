import os
import shutil
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch
from src.api import app, UPLOAD_DIR

client = TestClient(app)

def test_upload_file():
    # Setup
    filename = "test_upload.pdf"
    file_content = b"dummy pdf content"
    
    # Execute
    response = client.post(
        "/upload",
        files={"file": (filename, file_content, "application/pdf")}
    )
    
    # Verify
    assert response.status_code == 200
    assert response.json() == {"filename": filename, "message": "File uploaded successfully."}
    
    # Cleanup
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)

@patch("src.api.agent_app.ainvoke", new_callable=AsyncMock)
@patch("src.api.load_document")
def test_analyze_contract(mock_load, mock_invoke):
    # Setup
    filename = "test_analyze.pdf"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(b"dummy")
    
    msg_mock = MagicMock()
    msg_mock.page_content = "This is a contract."
    mock_load.return_value = [msg_mock]
    
    mock_invoke.return_value = {
        "extracted_data": {"compliance": [{"risk_level": "LOW"}]},
        "final_report": "This is a synthesized report."
    }
    
    # Execute
    response = client.post("/analyze", json={"filename": filename})
    
    # Verify
    assert response.status_code == 200
    data = response.json()
    assert "extracted_data" in data
    assert data["final_report"] == "This is a synthesized report."
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)
