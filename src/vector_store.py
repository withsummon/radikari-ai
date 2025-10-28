import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import openai
from typing import List, Dict, Any, Optional
import uuid
import os
from dotenv import load_dotenv
import logging

from .models import KnowledgeChunk, KnowledgeMetadata

load_dotenv()

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        
        # Initialize OpenAI embedding function
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=openai_api_key,
            model_name="text-embedding-ada-002"
        )
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"ChromaDB initialized with persist directory: {persist_directory}")

    def add_chunks(self, chunks: List[KnowledgeChunk]) -> List[str]:
        """Add knowledge chunks to the vector store"""
        try:
            documents = []
            metadatas = []
            ids = []
            
            for chunk in chunks:
                documents.append(chunk.content)
                
                # Prepare metadata for Chroma (must be flat dict with string/numeric values)
                metadata = {
                    "knowledge_id": chunk.knowledge_id,
                    "chunk_index": chunk.chunk_index,
                    "type": chunk.metadata.type,
                    "isGlobal": chunk.metadata.isGlobal,
                }
                
                # Add optional metadata fields
                if chunk.metadata.tenantId:
                    metadata["tenantId"] = chunk.metadata.tenantId
                
                if chunk.metadata.tenantRoleIds:
                    # Store as comma-separated string since Chroma doesn't support arrays
                    metadata["tenantRoleIds"] = ",".join(chunk.metadata.tenantRoleIds)
                
                metadatas.append(metadata)
                ids.append(chunk.id)
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(chunks)} chunks to vector store")
            return ids
            
        except Exception as e:
            logger.error(f"Error adding chunks to vector store: {e}")
            raise

    def search(
        self, 
        query: str, 
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks in the vector store"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and results["ids"][0]:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "relevance_score": 1 - results["distances"][0][i]  # Convert distance to relevance
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            raise

    def delete_by_knowledge_id(self, knowledge_id: str) -> bool:
        """Delete all chunks belonging to a specific knowledge item"""
        try:
            # Get all chunks for this knowledge_id
            results = self.collection.get(
                where={"knowledge_id": knowledge_id},
                include=["metadatas"]
            )
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} chunks for knowledge_id: {knowledge_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting chunks for knowledge_id {knowledge_id}: {e}")
            raise

    def update_metadata(self, knowledge_id: str, new_metadata: KnowledgeMetadata) -> bool:
        """Update metadata for all chunks of a knowledge item"""
        try:
            # Get all chunks for this knowledge_id
            results = self.collection.get(
                where={"knowledge_id": knowledge_id},
                include=["metadatas"]
            )
            
            if not results["ids"]:
                return False
            
            # Prepare updated metadata
            updated_metadatas = []
            for existing_metadata in results["metadatas"]:
                updated_metadata = {
                    "knowledge_id": knowledge_id,
                    "chunk_index": existing_metadata["chunk_index"],
                    "type": new_metadata.type,
                    "isGlobal": new_metadata.isGlobal,
                }
                
                if new_metadata.tenantId:
                    updated_metadata["tenantId"] = new_metadata.tenantId
                
                if new_metadata.tenantRoleIds:
                    updated_metadata["tenantRoleIds"] = ",".join(new_metadata.tenantRoleIds)
                
                updated_metadatas.append(updated_metadata)
            
            # Update metadata
            self.collection.update(
                ids=results["ids"],
                metadatas=updated_metadatas
            )
            
            logger.info(f"Updated metadata for {len(results['ids'])} chunks of knowledge_id: {knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating metadata for knowledge_id {knowledge_id}: {e}")
            raise

    def build_access_filter(self, user_attributes) -> Dict[str, Any]:
        """Build a filter for user access control based on user attributes"""
        # Users can access:
        # 1. Global knowledge (isGlobal = True)
        # 2. Knowledge with no tenantId (public within system)
        # 3. Knowledge where user has access to the tenant and role
        
        user_tenant_ids = [tenant.tenantId for tenant in user_attributes.userTenants]
        user_roles = [tenant.tenantRole for tenant in user_attributes.userTenants]
        
        # Build OR conditions for access
        or_conditions = []
        
        # Global knowledge
        or_conditions.append({"isGlobal": True})
        
        # Knowledge with no tenant restriction
        # Note: Chroma doesn't have a direct "field not exists" filter,
        # so we'll handle this in the application logic after retrieval
        
        # Knowledge for user's tenants
        for tenant in user_attributes.userTenants:
            tenant_condition = {"tenantId": tenant.tenantId}
            or_conditions.append(tenant_condition)
        
        # For now, return a simple filter - we'll do additional filtering in application logic
        return {"$or": or_conditions} if len(or_conditions) > 1 else or_conditions[0] if or_conditions else {}

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.collection.name
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}