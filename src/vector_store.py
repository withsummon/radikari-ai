
import os
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import uuid as uuid_lib
import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny

from .models import KnowledgeChunk, KnowledgeMetadata
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QdrantVectorStore:
    def __init__(self):
        """Initialize Qdrant vector store with Google GenAI embeddings"""
        logger.info("=== Starting Qdrant Vector Store Initialization ===")
        self.collection_name = "radikari_knowledge"
        
        # Initialize Qdrant Client
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        if not qdrant_url:
            raise ValueError("QDRANT_URL environment variable is required")
        
        logger.info(f"Connecting to Qdrant at: {qdrant_url}")
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
        )
        logger.info("✓ Successfully connected to Qdrant")
        
        # Initialize Google GenAI
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
            
        genai.configure(api_key=google_api_key)
        self.embedding_model = "gemini-embedding-001"
        logger.info("✓ Successfully configured Google GenAI")
        
        # Ensure collection exists
        self._ensure_collection()
        logger.info("=== Qdrant Vector Store Initialization Complete ===")

    def _ensure_collection(self):
        """Ensure the collection exists with correct config"""
        try:
            if not self.client.collection_exists(self.collection_name):
                logger.info(f"Creating collection {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
                )
                logger.info(f"✓ Successfully created collection {self.collection_name}")
            else:
                logger.info(f"✓ Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"✗ Failed to ensure collection exists: {e}")
            raise

    def _generate_embeddings(self, texts: List[str], task_type: str = "retrieval_document") -> List[List[float]]:
        """Generate embeddings using Google GenAI"""
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts with task_type: {task_type}")
            results = []
            
            for i, text in enumerate(texts):
                if i % 10 == 0:  # Log progress every 10 texts
                    logger.debug(f"Processing embedding {i+1}/{len(texts)}")
                
                embedding_result = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type=task_type,
                    output_dimensionality=768
                )
                
                # L2 Normalization
                embedding = np.array(embedding_result['embedding'])
                norm = np.linalg.norm(embedding)
                if norm > 0:
                    embedding = embedding / norm
                
                results.append(embedding.tolist())
            
            logger.debug(f"✓ Successfully generated {len(results)} embeddings")
            return results
        except Exception as e:
            logger.error(f"✗ Failed to generate embeddings: {e}")
            raise

    def add_chunks(self, chunks: List[KnowledgeChunk]) -> List[str]:
        """Add chunks to Qdrant"""
        try:
            logger.info(f"Adding {len(chunks)} chunks to Qdrant")
            texts = [chunk.content for chunk in chunks]
            embeddings = self._generate_embeddings(texts, task_type="retrieval_document")
            
            points = []
            for i, chunk in enumerate(chunks):
                # Validate chunk ID format
                chunk_id = chunk.id
                logger.debug(f"Processing chunk {i+1}/{len(chunks)} with ID: {chunk_id}")
                
                # Ensure ID is a valid UUID format for Qdrant
                try:
                    uuid_lib.UUID(chunk_id)
                    logger.debug(f"✓ Valid UUID confirmed: {chunk_id}")
                except ValueError:
                    logger.error(f"✗ Invalid UUID format: {chunk_id}")
                    raise ValueError(f"Chunk ID {chunk_id} is not a valid UUID format")
                
                # Flatten metadata for Qdrant payload
                payload = {
                    "knowledge_id": chunk.knowledge_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "type": chunk.metadata.type,
                    "isGlobal": chunk.metadata.isGlobal,
                    "tenantId": chunk.metadata.tenantId,
                    "headline": chunk.metadata.headline,
                    "tenantRoleIds": chunk.metadata.tenantRoleIds or []
                }
                
                points.append(PointStruct(
                    id=chunk_id,  # Validated UUID
                    vector=embeddings[i],
                    payload=payload
                ))

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"✓ Upserted {len(points)} points to Qdrant")
            return [p.id for p in points]
            
        except Exception as e:
            logger.error(f"✗ Error adding chunks to Qdrant: {e}")
            raise

    def delete_by_knowledge_id(self, knowledge_id: str) -> bool:
        """Delete points by knowledge_id"""
        try:
            logger.info(f"Deleting chunks for knowledge_id: {knowledge_id}")
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="knowledge_id",
                                match=models.MatchValue(value=knowledge_id)
                            )
                        ]
                    )
                )
            )
            logger.info(f"✓ Successfully deleted chunks for knowledge_id: {knowledge_id}")
            return True
        except Exception as e:
            logger.error(f"✗ Error deleting knowledge {knowledge_id}: {e}")
            raise

    def update_metadata(self, knowledge_id: str, new_metadata: KnowledgeMetadata) -> bool:
        """Update metadata for a knowledge ID"""
        try:
            logger.info(f"Updating metadata for knowledge_id: {knowledge_id}")
            payload = {
                "type": new_metadata.type,
                "isGlobal": new_metadata.isGlobal,
                "tenantId": new_metadata.tenantId,
                "headline": new_metadata.headline,
                "tenantRoleIds": new_metadata.tenantRoleIds or []
            }
            
            self.client.set_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="knowledge_id",
                            match=models.MatchValue(value=knowledge_id)
                        )
                    ]
                )
            )
            logger.info(f"✓ Successfully updated metadata for knowledge_id: {knowledge_id}")
            return True
        except Exception as e:
            logger.error(f"✗ Error updating metadata for {knowledge_id}: {e}")
            raise

    def search(self, query: str, n_results: int = 5, where_filter: Optional[Dict] = None) -> List[Dict]:
        """
        Search implementation.
        Note: The worker primarily writes, but this is useful for verification/testing.
        """
        try:
            logger.info(f"Searching for: '{query}' with {n_results} results")
            embedding_raw = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"
            )['embedding']
            
            embedding_np = np.array(embedding_raw)
            norm = np.linalg.norm(embedding_np)
            if norm > 0:
                embedding_np = embedding_np / norm
            embedding = embedding_np.tolist()
            
            # Convert dict filter to Qdrant Filter object if necessary
            query_filter = None
            if where_filter:
                # This would need to be implemented based on the filter structure
                # For now, we'll pass it as-is assuming it's already a Qdrant Filter
                query_filter = where_filter
            
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=n_results,
                query_filter=query_filter
            )
            
            formatted_results = [
                {
                    "id": hit.id,
                    "content": hit.payload.get("content"),
                    "metadata": hit.payload,
                    "score": hit.score,
                    "relevance_score": hit.score  # Qdrant uses similarity scores
                }
                for hit in results
            ]
            
            logger.info(f"✓ Found {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"✗ Error searching Qdrant: {e}")
            raise

    def build_access_filter(self, user_attributes) -> Optional[Filter]:
        """Build a filter for user access control based on user attributes"""
        # Check if filtering is disabled via environment variable
        no_filter = os.getenv("NO_FILTER", "false").lower() in ("true", "1", "yes", "on")
        
        if no_filter:
            logger.info("🚫 NO_FILTER is enabled - bypassing all access control filters")
            return None  # No filter means no restrictions
        
        # Users can access:
        # 1. Global knowledge (isGlobal = True)
        # 2. Knowledge with no tenantId (public within system)
        # 3. Knowledge where user has access to the tenant and role
        
        user_tenant_ids = [tenant.tenantId for tenant in user_attributes.userTenants]
        user_roles = [tenant.tenantRole for tenant in user_attributes.userTenants]
        
        # Build OR conditions for access
        or_conditions = []
        
        # Global knowledge
        or_conditions.append(FieldCondition(
            key="isGlobal",
            match=models.MatchValue(value=True)
        ))
        
        # Knowledge for user's tenants
        if user_tenant_ids:
            or_conditions.append(FieldCondition(
                key="tenantId",
                match=models.MatchAny(any=user_tenant_ids)
            ))
        
        # If we have conditions, create an OR filter
        if or_conditions:
            return Filter(must=or_conditions) if len(or_conditions) == 1 else Filter(should=or_conditions)
        
        return None

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "total_chunks": collection_info.points_count,
                "collection_name": self.collection_name,
                "vector_size": collection_info.config.params.vectors.size,
                "distance": collection_info.config.params.vectors.distance.value
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
