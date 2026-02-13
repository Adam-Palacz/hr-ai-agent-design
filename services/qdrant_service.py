"""
Qdrant RAG service for recruitment knowledge base.
"""
import os
import uuid
from typing import List, Dict, Optional, Union
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Azure OpenAI imports
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False

from core.logger import logger


class QdrantRAG:
    """Qdrant RAG service for vector database operations."""
    
    def __init__(
        self,
        collection_name: str = "recruitment_knowledge_base",
        use_azure_openai: bool = False,
        azure_endpoint: Optional[str] = None,
        azure_api_key: Optional[str] = None,
        azure_deployment: Optional[str] = None,
        azure_api_version: Optional[str] = None,
        qdrant_path: Optional[str] = None,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None
    ):
        """
        Initialize Qdrant RAG service.
        
        Args:
            collection_name: Collection name
            use_azure_openai: Whether to use Azure OpenAI embeddings
            azure_endpoint: Azure OpenAI endpoint URL
            azure_api_key: Azure OpenAI API key
            azure_deployment: Deployment name (e.g., "text-embedding-3-small")
            azure_api_version: Azure OpenAI API version
            qdrant_path: Path to local Qdrant database (None = in-memory or server)
            qdrant_host: Qdrant server hostname (e.g., "qdrant" or "localhost")
            qdrant_port: Qdrant server port (default: 6333)
        """
        # Initialize Qdrant client
        # Priority: server (host+port) > local path > in-memory
        if qdrant_host:
            # Connect to Qdrant server
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
                else:
                    raise
        else:
            self.client = QdrantClient(":memory:")  # In-memory
            logger.info("Qdrant in-memory database")
        
        self.collection_name = collection_name
        
        # Initialize Azure OpenAI if needed
        if use_azure_openai and azure_endpoint and azure_api_key:
            if not AZURE_OPENAI_AVAILABLE:
                raise ImportError("openai is not installed. Run: pip install openai")
            
            self.azure_client = AzureOpenAI(
                api_version=azure_api_version or "2024-12-01-preview",
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key
            )
            self.azure_deployment = azure_deployment or "text-embedding-3-small"
            self.use_azure_openai = True
            logger.info(f"Using Azure OpenAI embeddings (deployment: {self.azure_deployment})")
        else:
            self.use_azure_openai = False
            raise ValueError("Azure OpenAI credentials must be provided")
        
        # Create collection if it doesn't exist
        try:
            self.client.get_collection(collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except:
            # Create new collection
            # text-embedding-3-small has 1536 dimensions
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=1536,  # text-embedding-3-small
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created new collection: {collection_name}")
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        if not self.use_azure_openai:
            raise ValueError("Azure OpenAI is not configured")
        
        response = self.azure_client.embeddings.create(
            input=texts,
            model=self.azure_deployment,
            timeout=60.0
        )
        
        # Return embeddings in order matching input
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        
        return embeddings
    
    def add_documents(
        self,
        documents: List[str],
        ids: Optional[List[Union[str, int, uuid.UUID]]] = None,
        metadatas: Optional[List[Dict]] = None
    ):
        """Add documents to collection."""
        if ids is None:
            # Generate UUID for each document
            ids = [uuid.uuid4() for _ in range(len(documents))]
        else:
            # Convert string IDs to UUID if needed
            converted_ids = []
            for id_val in ids:
                if isinstance(id_val, str):
                    try:
                        converted_ids.append(uuid.UUID(id_val))
                    except ValueError:
                        # If not UUID, generate new UUID
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
        
        logger.info(f"Saving to Qdrant...")
        points = [
            PointStruct(
                id=ids[i],
                vector=embeddings[i],
                payload={
                    "document": documents[i],
                    "original_id": str(ids[i]),  # Save original ID in payload
                    **metadatas[i]
                }
            )
            for i in range(len(documents))
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Added {len(documents)} documents to collection")
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for similar documents."""
        logger.debug(f"Generating embedding for query: {query[:50]}...")
        query_embedding = self._generate_embeddings([query])[0]
        
        logger.debug(f"Searching in Qdrant...")
        # Use search API (works with Qdrant 1.8.4+)
        try:
            # Try search method first (standard API)
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=n_results
            )
        except (AttributeError, Exception) as e:
            # Fallback for older Qdrant versions or different API
            logger.warning(f"Search method failed ({e}), trying alternative API...")
            try:
                # Try scroll with vectors (for manual similarity calculation)
                scroll_results = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,  # Get more points to calculate similarity
                    with_payload=True,
                    with_vectors=True  # Need vectors for similarity calculation
                )
                # Calculate distances manually (simple cosine similarity)
                import numpy as np
                query_vec = np.array(query_embedding)
                scored_results = []
                for point in scroll_results[0]:
                    if point.vector:
                        point_vec = np.array(point.vector)
                        # Cosine similarity
                        similarity = np.dot(query_vec, point_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(point_vec))
                        scored_results.append((point, similarity))
                
                # Sort by similarity and take top n
                scored_results.sort(key=lambda x: x[1], reverse=True)
                results = [point for point, score in scored_results[:n_results]]
            except Exception as e2:
                logger.error(f"All search methods failed: {e2}")
                return []
        
        formatted_results = []
        for point in results:
            # Handle both search result format and scroll format
            point_id = point.id if hasattr(point, 'id') else getattr(point, 'id', None)
            point_payload = point.payload if hasattr(point, 'payload') else getattr(point, 'payload', {})
            point_score = point.score if hasattr(point, 'score') else getattr(point, 'score', None)
            
            formatted_results.append({
                'id': str(point_id),  # Convert UUID to string
                'document': point_payload.get('document', ''),
                'metadata': {k: v for k, v in point_payload.items() if k not in ['document', 'original_id']},
                'distance': point_score
            })
        
        logger.debug(f"Found {len(formatted_results)} results")
        return formatted_results
    
    def count(self) -> int:
        """Return number of documents in collection."""
        info = self.client.get_collection(self.collection_name)
        return info.points_count
    
    def get_all(self) -> List[Dict]:
        """Get all documents from collection."""
        results = self.client.scroll(
            collection_name=self.collection_name,
            limit=10000  # Large limit
        )
        
        formatted_results = []
        for point in results[0]:  # results[0] is list of points
            formatted_results.append({
                'id': point.id,
                'document': point.payload.get('document', ''),
                'metadata': {k: v for k, v in point.payload.items() if k != 'document'}
            })
        
        return formatted_results

