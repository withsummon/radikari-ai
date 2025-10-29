import chromadb
from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE
from chromadb.utils import embedding_functions
import logging
import os
from typing import List, Dict, Any, Optional
import uuid
import os
from dotenv import load_dotenv
import logging
import traceback

from .models import KnowledgeChunk, KnowledgeMetadata

load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ChromaVectorStore:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """Initialize ChromaDB vector store with local persistence only."""
        logger.info("=== Starting ChromaDB Vector Store Initialization (Local Mode) ===")
        self.persist_directory = persist_directory
        logger.debug(f"Persist directory: {persist_directory}")
        
        # Use local ChromaDB only - no remote connection
        try:
            logger.info(f"Using local ChromaDB with persist directory: {persist_directory}")
            self.client = chromadb.PersistentClient(path=persist_directory)
            logger.info("✓ Successfully created PersistentClient")
        except Exception as e:
            logger.error(f"✗ Failed to create ChromaDB client: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        
        # Initialize embedding function
        try:
            logger.info("Initializing SentenceTransformer embedding function...")
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            logger.info("✓ Successfully initialized embedding function")
        except Exception as e:
            logger.error(f"✗ Failed to initialize embedding function: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            raise
        
        # Get or create collection with ChromaDB latest version approach
        logger.info("Attempting to get or create ChromaDB collection...")
        try:
            logger.debug("Trying with embedding function...")
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base",
                embedding_function=self.embedding_function
            )
            logger.info("✓ Successfully initialized ChromaDB collection with embedding function")
        except Exception as e:
            logger.warning(f"Failed to create collection with embedding function: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            # Fallback: try without embedding function
            try:
                logger.debug("Trying without embedding function...")
                self.collection = self.client.get_or_create_collection(name="knowledge_base")
                logger.info("✓ Successfully created collection without embedding function")
            except Exception as e2:
                logger.error(f"✗ Failed to create collection even without embedding function: {e2}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                raise e2
        
        logger.info("=== ChromaDB Vector Store Initialization Complete ===")
        
        # Test the connection
        try:
            logger.info("Testing ChromaDB connection...")
            collection_count = self.collection.count()
            logger.info(f"✓ Connection test successful. Collection has {collection_count} documents")
        except Exception as e:
            logger.error(f"✗ Connection test failed: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base",
                embedding_function=self.embedding_function
            )
            logger.info("Successfully initialized collection 'knowledge_base'")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
            # Fallback without embedding function
            self.collection = self.client.get_or_create_collection(name="knowledge_base")
            logger.info("Initialized collection without embedding function")
        
        if chroma_host:
            logger.info(f"ChromaDB initialized with remote server: {chroma_host}:{chroma_port}")
        else:
            logger.info(f"ChromaDB initialized with persist directory: {persist_directory}")
        
    def _ensure_tenant_and_database(self, admin_client, tenant: str, database: str):
        """Ensure tenant and database exist, create them if they don't."""
        # For default tenant, it should already exist in most ChromaDB setups
        if tenant == DEFAULT_TENANT:
            logger.info(f"Using default tenant '{tenant}' - should already exist")
        else:
            try:
                # Try to get the tenant
                admin_client.get_tenant(name=tenant)
                logger.info(f"Tenant '{tenant}' already exists")
            except Exception as e:
                # Tenant doesn't exist, create it
                logger.info(f"Creating tenant '{tenant}'")
                try:
                    admin_client.create_tenant(name=tenant)
                except Exception as create_error:
                    logger.error(f"Failed to create tenant '{tenant}': {create_error}")
                    raise
            
        # For default database, it should already exist in most ChromaDB setups
        if database == DEFAULT_DATABASE:
            logger.info(f"Using default database '{database}' - should already exist")
        else:
            try:
                # Try to get the database
                admin_client.get_database(name=database, tenant=tenant)
                logger.info(f"Database '{database}' already exists in tenant '{tenant}'")
            except Exception as e:
                # Database doesn't exist, create it
                logger.info(f"Creating database '{database}' in tenant '{tenant}'")
                try:
                    admin_client.create_database(name=database, tenant=tenant)
                except Exception as create_error:
                    logger.error(f"Failed to create database '{database}': {create_error}")
                    raise

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