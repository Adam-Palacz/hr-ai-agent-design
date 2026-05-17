"""
Qdrant RAG service for recruitment knowledge base.
"""

import uuid
from typing import List, Dict, Optional, Union, Literal

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

try:
    from openai import AzureOpenAI, OpenAI

    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    AzureOpenAI = None  # type: ignore[misc, assignment]
    OpenAI = None  # type: ignore[misc, assignment]

from core.logger import logger

EmbeddingProvider = Literal["azure", "openai"]
EMBEDDING_VECTOR_SIZE = 1536  # text-embedding-3-small


def create_qdrant_rag(
    collection_name: str = "recruitment_knowledge_base",
    *,
    qdrant_host: Optional[str] = None,
    qdrant_port: Optional[int] = None,
    qdrant_path: Optional[str] = None,
) -> "QdrantRAG":
    """
    Build QdrantRAG using ``LLM_PROVIDER`` from settings (azure or openai).

    Raises:
        RuntimeError: if required credentials for the selected provider are missing.
    """
    from config import settings

    qdrant_kwargs = {
        "collection_name": collection_name,
        "qdrant_host": qdrant_host,
        "qdrant_port": qdrant_port,
        "qdrant_path": qdrant_path,
    }

    if settings.uses_openai_provider:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set in .env. "
                "Required for embeddings when LLM_PROVIDER=openai."
            )
        return QdrantRAG(
            embedding_provider="openai",
            openai_api_key=settings.openai_api_key,
            openai_base_url=settings.openai_base_url,
            openai_embedding_model=settings.openai_embedding_model,
            **qdrant_kwargs,
        )

    if not settings.azure_openai_api_key:
        raise RuntimeError(
            "AZURE_OPENAI_API_KEY is not set in .env. "
            "Required for embeddings when LLM_PROVIDER=azure (recommended for production)."
        )
    return QdrantRAG(
        embedding_provider="azure",
        azure_endpoint=settings.azure_openai_endpoint,
        azure_api_key=settings.azure_openai_api_key,
        azure_deployment=settings.azure_openai_embedding_deployment,
        azure_api_version=settings.azure_openai_api_version,
        **qdrant_kwargs,
    )


class QdrantRAG:
    """Qdrant RAG service for vector database operations."""

    def __init__(
        self,
        collection_name: str = "recruitment_knowledge_base",
        *,
        embedding_provider: EmbeddingProvider = "azure",
        use_azure_openai: Optional[bool] = None,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_deployment: Optional[str] = None,
        azure_api_version: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        openai_embedding_model: Optional[str] = None,
        qdrant_path: Optional[str] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
    ):
        if use_azure_openai is not None:
            embedding_provider = "azure" if use_azure_openai else "openai"
        self.embedding_provider: EmbeddingProvider = embedding_provider.lower()  # type: ignore[assignment]

        if qdrant_host:
            qdrant_port = qdrant_port or 6333
            self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
            logger.info(f"Qdrant server connection: {qdrant_host}:{qdrant_port}")
        elif qdrant_path:
            try:
                self.client = QdrantClient(path=qdrant_path)
                logger.info(f"Qdrant local database: {qdrant_path}")
            except RuntimeError as e:
                if "already accessed by another instance" in str(e) or "AlreadyLocked" in str(e):
                    error_msg = (
                        f"Qdrant database at {qdrant_path} is already locked by another instance. "
                        "Close other Qdrant clients (e.g., app.py) before accessing. "
                        "Consider using Qdrant server (qdrant_host/qdrant_port) instead."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg) from e
                raise
        else:
            self.client = QdrantClient(":memory:")
            logger.info("Qdrant in-memory database")

        self.collection_name = collection_name
        self._init_embedding_client(
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_api_key,
            azure_deployment=azure_deployment,
            azure_api_version=azure_api_version,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            openai_embedding_model=openai_embedding_model,
        )
        self._ensure_collection()

    def _init_embedding_client(
        self,
        *,
        azure_endpoint: Optional[str],
        azure_api_key: Optional[str],
        azure_deployment: Optional[str],
        azure_api_version: Optional[str],
        openai_api_key: Optional[str],
        openai_base_url: Optional[str],
        openai_embedding_model: Optional[str],
    ) -> None:
        if not OPENAI_SDK_AVAILABLE:
            raise ImportError("openai is not installed. Run: pip install openai")

        if self.embedding_provider == "azure":
            if not (azure_endpoint and azure_api_key):
                raise ValueError("Azure OpenAI credentials are required for Azure embeddings")
            self.embedding_client = AzureOpenAI(
                api_version=azure_api_version or "2024-12-01-preview",
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
            )
            self.embedding_model = azure_deployment or "text-embedding-3-small"
            logger.info(f"Embeddings: Azure OpenAI (deployment: {self.embedding_model})")
        elif self.embedding_provider == "openai":
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings")
            client_kwargs = {"api_key": openai_api_key}
            if openai_base_url:
                client_kwargs["base_url"] = openai_base_url
            self.embedding_client = OpenAI(**client_kwargs)
            self.embedding_model = openai_embedding_model or "text-embedding-3-small"
            logger.info(f"Embeddings: OpenAI API (model: {self.embedding_model})")
        else:
            raise ValueError(f"Unknown embedding provider: {self.embedding_provider}")

    def _ensure_collection(self) -> None:
        try:
            self.client.get_collection(self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=EMBEDDING_VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        response = self.embedding_client.embeddings.create(
            input=texts, model=self.embedding_model, timeout=60.0
        )
        embeddings: List[List[float]] = [[] for _ in range(len(texts))]
        for item in response.data:
            embeddings[item.index] = item.embedding
        return embeddings

    def add_documents(
        self,
        documents: List[str],
        ids: Optional[List[Union[str, int, uuid.UUID]]] = None,
        metadatas: Optional[List[Dict]] = None,
    ):
        """Add documents to collection."""
        if ids is None:
            ids = [uuid.uuid4() for _ in range(len(documents))]
        else:
            converted_ids: List[Union[str, int, uuid.UUID]] = []
            for id_val in ids:
                if isinstance(id_val, str):
                    try:
                        converted_ids.append(uuid.UUID(id_val))
                    except ValueError:
                        converted_ids.append(uuid.uuid4())
                elif isinstance(id_val, int):
                    converted_ids.append(id_val)
                else:
                    converted_ids.append(id_val)
            ids = converted_ids

        if metadatas is None:
            metadatas = [{}] * len(documents)

        logger.info(f"Generating embeddings for {len(documents)} documents...")
        embeddings = self._generate_embeddings(documents)
        logger.info(f"Generated {len(embeddings)} embeddings")

        logger.info("Saving to Qdrant...")
        points = [
            PointStruct(
                id=ids[i],
                vector=embeddings[i],
                payload={
                    "document": documents[i],
                    "original_id": str(ids[i]),
                    **metadatas[i],
                },
            )
            for i in range(len(documents))
        ]

        self.client.upsert(collection_name=self.collection_name, points=points)
        logger.info(f"Added {len(documents)} documents to collection")

    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for similar documents."""
        logger.debug(f"Generating embedding for query: {query[:50]}...")
        query_embedding = self._generate_embeddings([query])[0]

        logger.debug("Searching in Qdrant...")
        try:
            results = self.client.search(
                collection_name=self.collection_name, query_vector=query_embedding, limit=n_results
            )
        except (AttributeError, Exception) as e:
            logger.warning(f"Search method failed ({e}), trying alternative API...")
            try:
                scroll_results = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    with_payload=True,
                    with_vectors=True,
                )
                import numpy as np

                query_vec = np.array(query_embedding)
                scored_results = []
                for point in scroll_results[0]:
                    if point.vector:
                        point_vec = np.array(point.vector)
                        similarity = np.dot(query_vec, point_vec) / (
                            np.linalg.norm(query_vec) * np.linalg.norm(point_vec)
                        )
                        scored_results.append((point, similarity))
                scored_results.sort(key=lambda x: x[1], reverse=True)
                results = [point for point, _ in scored_results[:n_results]]
            except Exception as e2:
                logger.error(f"All search methods failed: {e2}")
                return []

        formatted_results = []
        for point in results:
            point_id = point.id if hasattr(point, "id") else getattr(point, "id", None)
            point_payload = (
                point.payload if hasattr(point, "payload") else getattr(point, "payload", {})
            )
            point_score = point.score if hasattr(point, "score") else getattr(point, "score", None)

            formatted_results.append(
                {
                    "id": str(point_id),
                    "document": point_payload.get("document", ""),
                    "metadata": {
                        k: v
                        for k, v in point_payload.items()
                        if k not in ["document", "original_id"]
                    },
                    "distance": point_score,
                }
            )

        logger.debug(f"Found {len(formatted_results)} results")
        return formatted_results

    def count(self) -> int:
        """Return number of documents in collection."""
        info = self.client.get_collection(self.collection_name)
        return info.points_count

    def get_all(self) -> List[Dict]:
        """Get all documents from collection."""
        results = self.client.scroll(collection_name=self.collection_name, limit=10000)

        formatted_results = []
        for point in results[0]:
            formatted_results.append(
                {
                    "id": point.id,
                    "document": point.payload.get("document", ""),
                    "metadata": {k: v for k, v in point.payload.items() if k != "document"},
                }
            )

        return formatted_results
