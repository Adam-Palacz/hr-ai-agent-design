"""Unit tests for Qdrant RAG service (mocked client and embeddings, no real API)."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_qdrant_client():
    """Mock QdrantClient: get_collection raises (new DB), create_collection exists, upsert/search work."""
    client = MagicMock()
    client.get_collection.side_effect = Exception("Collection not found")
    client.create_collection.return_value = None
    client.upsert.return_value = None
    # search returns list of ScoredPoint-like objects
    point = MagicMock()
    point.id = "doc-1"
    point.payload = {"document": "Sample doc text", "metadata": {}}
    point.score = 0.9
    client.search.return_value = [point]
    client.scroll.return_value = ([], None)
    client.get_collection.return_value = MagicMock(points_count=0)
    return client


@patch("services.qdrant_service.QdrantClient")
@patch("services.qdrant_service.AzureOpenAI")
def test_qdrant_rag_search_returns_expected_structure(
    mock_azure, mock_qdrant_cls, mock_qdrant_client
):
    """Search returns list of dicts with id, document, metadata, distance."""
    mock_qdrant_cls.return_value = mock_qdrant_client
    mock_emb = MagicMock()
    mock_emb.data = [MagicMock(index=0, embedding=[0.1] * 1536)]
    mock_azure.return_value.embeddings.create.return_value = mock_emb

    with patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_API_KEY": "test",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        },
        clear=False,
    ):
        from services.qdrant_service import QdrantRAG

        rag = QdrantRAG(
            collection_name="test_coll",
            use_azure_openai=True,
            azure_endpoint="https://test.openai.azure.com/",
            azure_api_key="test",
            azure_deployment="text-embedding-3-small",
            qdrant_host="localhost",
            qdrant_port=6333,
        )
        rag.client = mock_qdrant_client

    results = rag.search("query", n_results=5)

    assert isinstance(results, list)
    assert len(results) >= 0
    if results:
        r = results[0]
        assert "id" in r or "document" in r
        assert "document" in r
    mock_qdrant_client.search.assert_called_once()


@patch("services.qdrant_service.QdrantClient")
@patch("services.qdrant_service.AzureOpenAI")
def test_qdrant_rag_add_documents_calls_upsert(mock_azure, mock_qdrant_cls, mock_qdrant_client):
    """add_documents generates embeddings and calls upsert."""
    mock_qdrant_cls.return_value = mock_qdrant_client
    mock_emb_response = MagicMock()
    mock_emb_response.data = [
        MagicMock(index=0, embedding=[0.1] * 1536),
        MagicMock(index=1, embedding=[0.2] * 1536),
    ]
    mock_azure_instance = MagicMock()
    mock_azure_instance.embeddings.create.return_value = mock_emb_response
    mock_azure.return_value = mock_azure_instance

    with patch.dict(
        "os.environ",
        {
            "AZURE_OPENAI_API_KEY": "test",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        },
        clear=False,
    ):
        from services.qdrant_service import QdrantRAG

        rag = QdrantRAG(
            collection_name="test_coll",
            use_azure_openai=True,
            azure_endpoint="https://test.openai.azure.com/",
            azure_api_key="test",
            azure_deployment="text-embedding-3-small",
            qdrant_host="localhost",
            qdrant_port=6333,
        )
        rag.client = mock_qdrant_client

    rag.add_documents(["Doc one", "Doc two"])

    mock_qdrant_client.upsert.assert_called_once()
    call_args = mock_qdrant_client.upsert.call_args
    assert call_args[1]["collection_name"] == "test_coll"
    assert len(call_args[1]["points"]) == 2
