import os
import pytest
from unittest.mock import MagicMock, patch
from src.ingest import load_document, split_documents
from langchain_core.documents import Document

# Sample data
SAMPLE_TEXT = "This is a sample contract text. " * 50

@pytest.fixture
def mock_pdf_loader():
    with patch("src.ingest.PyPDFLoader") as MockLoader:
        mock_instance = MockLoader.return_value
        mock_instance.load.return_value = [Document(page_content="PDF Content", metadata={"source": "test.pdf"})]
        yield MockLoader

@pytest.fixture
def mock_docx_loader():
    with patch("src.ingest.Docx2txtLoader") as MockLoader:
        mock_instance = MockLoader.return_value
        mock_instance.load.return_value = [Document(page_content="DOCX Content", metadata={"source": "test.docx"})]
        yield MockLoader

def test_load_document_pdf(mock_pdf_loader):
    docs = load_document("test.pdf")
    assert len(docs) == 1
    assert docs[0].page_content == "PDF Content"
    mock_pdf_loader.assert_called_once_with("test.pdf")

def test_load_document_docx(mock_docx_loader):
    docs = load_document("test.docx")
    assert len(docs) == 1
    assert docs[0].page_content == "DOCX Content"
    mock_docx_loader.assert_called_once_with("test.docx")

def test_load_document_unsupported():
    with pytest.raises(ValueError):
        load_document("test.xyz")

def test_split_documents():
    doc = Document(page_content=SAMPLE_TEXT, metadata={"source": "test"})
    splits = split_documents([doc], chunk_size=100, chunk_overlap=10)
    assert len(splits) > 1
    assert isinstance(splits[0], Document)
    assert splits[0].metadata["source"] == "test"
