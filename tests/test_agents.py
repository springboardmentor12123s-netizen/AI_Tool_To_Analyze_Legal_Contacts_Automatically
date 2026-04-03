import pytest
from unittest.mock import MagicMock, patch
from src.agent_graph import app, retrieve_context

@pytest.fixture
def mock_vector_store():
    with patch("src.agent_graph.vector_store") as mock_vs:
        mock_vs.similarity_search.return_value = [
            MagicMock(page_content="Relevant clause 1"),
            MagicMock(page_content="Relevant clause 2")
        ]
        yield mock_vs

@pytest.fixture
def mock_llm():
    with patch("src.agent_graph.llm") as mock_l:
        mock_response = MagicMock()
        mock_response.content = "Analysis result"
        mock_l.invoke.return_value = mock_response
        yield mock_l

def test_retrieve_context(mock_vector_store):
    context = retrieve_context("query")
    assert "Relevant clause 1" in context
    assert "Relevant clause 2" in context
    mock_vector_store.similarity_search.assert_called()

def test_agent_graph_execution(mock_vector_store, mock_llm):
    # Test that the graph runs without error and returns expected keys
    initial_state = {
        "contract_text": "dummy text",
        "compliance_analysis": "",
        "finance_analysis": "",
        "legal_analysis": "",
        "operations_analysis": ""
    }
    
    # We mock the internal node functions' dependencies (llm, vector_store)
    # The app.invoke will call the real node functions, which utilize the mocks
    result = app.invoke(initial_state)
    
    assert "compliance_analysis" in result
    assert result["compliance_analysis"] == "Analysis result"
    assert result["finance_analysis"] == "Analysis result"
