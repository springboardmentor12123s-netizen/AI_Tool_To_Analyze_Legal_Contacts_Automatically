import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.agent_graph import app
from src.agent_graph import AgentState

@pytest.fixture
def mock_parallel_extractor():
    with patch("src.agent_graph.ParallelExtractor") as mock_pe_class:
        mock_instance = MagicMock()
        mock_instance.parallel_extract_all = AsyncMock(return_value={
            "compliance": [{"risk_level": "HIGH"}],
            "financial_risk": [{"exposure_amount": "$1M"}],
            "legal": [{"legal_risk": "MEDIUM"}],
            "operations": [{"feasibility_risk": "LOW"}]
        })
        mock_pe_class.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_pinecone_store():
    with patch("src.agent_graph.vector_store_manager") as mock_vsm:
        # Mock retrieval for 4 domains
        retrieved_mocks = [
            {"metadata": {"text": "dummy risk", "risk_level": "HIGH"}},
            {"metadata": {"text": "dummy exposure", "exposure_amount": "$1M"}},
            {"metadata": {"text": "dummy legal risk", "legal_risk": "MEDIUM"}},
            {"metadata": {"text": "dummy ops risk", "feasibility_risk": "LOW"}}
        ]
        # Just return the same mock regardless of domain for simplicity in test
        mock_vsm.retrieve_similar.return_value = retrieved_mocks
        yield mock_vsm

@pytest.fixture
def mock_llm():
    with patch("src.agent_graph.llm") as mock_l:
        mock_response = MagicMock()
        mock_response.content = "Multi-Domain Executive Summary"
        mock_l.invoke.return_value = mock_response
        yield mock_l

def test_agent_graph_execution(mock_parallel_extractor, mock_pinecone_store, mock_llm):
    # Test that the modern async graph runs without error
    initial_state = {
        "contract_text": "This is a dummy contract.\n\n" + "This clause is long enough to pass the fifty character minimum threshold required by the chunking node.",
        "clauses": [],
        "extracted_data": {},
        "final_report": ""
    }
    
    # We mock the internal node dependencies (ParallelExtractor, VectorStore, LLM)
    result = asyncio.run(app.ainvoke(initial_state))
    
    # Verify State Shape
    assert "extracted_data" in result
    assert "compliance" in result["extracted_data"]
    assert "legal" in result["extracted_data"]
    assert "final_report" in result
    assert result["final_report"] == "Multi-Domain Executive Summary"
    
    # Verify Mocks Were Called
    mock_parallel_extractor.parallel_extract_all.assert_called()
    mock_pinecone_store.store_clause.assert_called()
    mock_pinecone_store.retrieve_similar.assert_called()
    mock_llm.invoke.assert_called()
