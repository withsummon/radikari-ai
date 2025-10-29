import uuid
import logging
from typing import List, Dict, Any
from datetime import datetime
import re

from .models import (
    Knowledge, KnowledgeChunk, KnowledgeMetadata,
    AddKnowledgeRequest, AddKnowledgeResponse,
    UpdateKnowledgeMetadataRequest, UpdateKnowledgeMetadataResponse,
    DeleteKnowledgeRequest, DeleteKnowledgeResponse,
    KnowledgeCreateMessage, KnowledgeUpdateMessage, KnowledgeDeleteMessage
)
from .vector_store import ChromaVectorStore
from .mq_handler import MQHandler
from .pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class TextChunker:
    """Handles text chunking for knowledge documents"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        # Clean the text
        text = self._clean_text(text)
        
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # If we're not at the end, try to break at a sentence or word boundary
            if end < len(text):
                # Look for sentence endings
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundaries
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + self.chunk_size // 2:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere with processing
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)
        return text.strip()


class KnowledgeService:
    """Service for managing knowledge operations"""
    
    def __init__(self, vector_store: ChromaVectorStore):
        self.vector_store = vector_store
        self.text_chunker = TextChunker()
        self.knowledge_store: Dict[str, Knowledge] = {}  # In-memory store for knowledge metadata
        self.pdf_processor = PDFProcessor()
        
    def process_knowledge_create_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process KNOWLEDGE_CREATE message from RabbitMQ"""
        try:
            # Parse the message
            message = KnowledgeCreateMessage(**message_data)
            
            # Process content based on file type
            content = message.content
            
            if message.fileType == "pdf" and message.fileUrls:
                logger.info(f"Processing PDF files for knowledge {message.metadata.knowledgeId}")
                try:
                    pdf_text = self.pdf_processor.process_pdf_urls(message.fileUrls)
                    if pdf_text.strip():
                        content = f"{content}\n\n{pdf_text}"
                    else:
                        logger.warning("No text extracted from PDF files")
                except Exception as e:
                    logger.error(f"Failed to process PDF files: {e}")
                    # Continue with original content if PDF processing fails
            
            # Convert to internal format
            metadata = KnowledgeMetadata(
                tenantId=message.metadata.tenantId,
                tenantRoleIds=message.metadata.accessUserIds or [],
                type="ARTICLE" if message.metadata.type == "ARTICLE" else "FILE",
                isGlobal=(message.metadata.access == "PUBLIC")
            )
            
            # Create knowledge using existing method
            request_data = {
                "content": content,
                "metadata": metadata.dict(),
                "filetype": message.fileType,
                "url": message.fileUrls[0] if message.fileUrls else None
            }
            
            # Override the knowledge ID to use the one from the message
            knowledge_id = message.metadata.knowledgeId
            
            # Create knowledge object
            knowledge = Knowledge(
                id=knowledge_id,
                content=content,
                metadata=metadata,
                filetype=message.fileType,
                url=message.fileUrls[0] if message.fileUrls else None,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Chunk the content
            chunks_text = self.text_chunker.chunk_text(content)
            
            # Create chunks and add to vector store
            chunk_ids = []
            for i, chunk_text in enumerate(chunks_text):
                chunk_id = f"{knowledge_id}_chunk_{i}"
                chunk = KnowledgeChunk(
                    id=chunk_id,
                    knowledge_id=knowledge_id,
                    content=chunk_text,
                    metadata=metadata,
                    chunk_index=i
                )
                
                # Add to vector store
                self.vector_store.add_document(
                    doc_id=chunk_id,
                    content=chunk_text,
                    metadata={
                        "knowledge_id": knowledge_id,
                        "chunk_index": i,
                        "tenantId": metadata.tenantId,
                        "tenantRoleIds": metadata.tenantRoleIds,
                        "type": metadata.type,
                        "isGlobal": metadata.isGlobal,
                        "filetype": message.fileType,
                        "access": message.metadata.access,
                        "accessUserIds": message.metadata.accessUserIds or []
                    }
                )
                chunk_ids.append(chunk_id)
            
            # Store knowledge metadata
            self.knowledge_store[knowledge_id] = knowledge
            
            logger.info(f"Successfully created knowledge {knowledge_id} with {len(chunk_ids)} chunks")
            
            return {
                "status": "success",
                "knowledge_id": knowledge_id,
                "chunk_ids": chunk_ids,
                "message": f"Knowledge created with {len(chunk_ids)} chunks"
            }
            
        except Exception as e:
            logger.error(f"Failed to process knowledge create message: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def process_knowledge_update_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process KNOWLEDGE_UPDATE message from RabbitMQ"""
        try:
            # Parse the message
            message = KnowledgeUpdateMessage(**message_data)
            
            # First delete existing knowledge
            delete_result = self.process_knowledge_delete_message({"knowledgeId": message.metadata.knowledgeId})
            if delete_result["status"] != "success":
                logger.warning(f"Failed to delete existing knowledge during update: {delete_result}")
            
            # Then create new knowledge with updated content
            create_result = self.process_knowledge_create_message(message_data)
            
            if create_result["status"] == "success":
                logger.info(f"Successfully updated knowledge {message.metadata.knowledgeId}")
                return {
                    "status": "success",
                    "knowledge_id": message.metadata.knowledgeId,
                    "message": "Knowledge updated successfully"
                }
            else:
                return create_result
                
        except Exception as e:
            logger.error(f"Failed to process knowledge update message: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def process_knowledge_delete_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process KNOWLEDGE_DELETE message from RabbitMQ"""
        try:
            # Parse the message
            message = KnowledgeDeleteMessage(**message_data)
            knowledge_id = message.knowledgeId
            
            # Delete from vector store
            deleted_chunks = self.vector_store.delete_by_knowledge_id(knowledge_id)
            
            # Remove from knowledge store
            if knowledge_id in self.knowledge_store:
                del self.knowledge_store[knowledge_id]
            
            logger.info(f"Successfully deleted knowledge {knowledge_id} with {deleted_chunks} chunks")
            
            return {
                "status": "success",
                "knowledge_id": knowledge_id,
                "deleted_chunks": deleted_chunks,
                "message": f"Knowledge deleted with {deleted_chunks} chunks"
            }
            
        except Exception as e:
            logger.error(f"Failed to process knowledge delete message: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
        
    def add_knowledge(self, request_data: Dict[str, Any]) -> AddKnowledgeResponse:
        """Add new knowledge to the system"""
        try:
            # Parse request
            request = AddKnowledgeRequest(**request_data)
            
            # Create knowledge object
            knowledge_id = str(uuid.uuid4())
            knowledge = Knowledge(
                id=knowledge_id,
                content=request.content,
                metadata=request.metadata,
                filetype=request.filetype,
                url=request.url,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Chunk the content
            chunks_text = self.text_chunker.chunk_text(request.content)
            
            # Create knowledge chunks
            chunks = []
            chunk_ids = []
            
            for i, chunk_text in enumerate(chunks_text):
                chunk_id = f"{knowledge_id}_chunk_{i}"
                chunk = KnowledgeChunk(
                    id=chunk_id,
                    knowledge_id=knowledge_id,
                    content=chunk_text,
                    metadata=request.metadata,
                    chunk_index=i
                )
                chunks.append(chunk)
                chunk_ids.append(chunk_id)
            
            # Add chunks to vector store
            self.vector_store.add_chunks(chunks)
            
            # Store knowledge metadata
            self.knowledge_store[knowledge_id] = knowledge
            
            logger.info(f"Added knowledge {knowledge_id} with {len(chunks)} chunks")
            
            return AddKnowledgeResponse(
                knowledge_id=knowledge_id,
                chunk_ids=chunk_ids,
                status="success"
            )
            
        except Exception as e:
            logger.error(f"Error adding knowledge: {e}")
            return AddKnowledgeResponse(
                knowledge_id="",
                chunk_ids=[],
                status=f"error: {str(e)}"
            )
    
    def update_knowledge_metadata(self, request_data: Dict[str, Any]) -> UpdateKnowledgeMetadataResponse:
        """Update metadata for existing knowledge"""
        try:
            request = UpdateKnowledgeMetadataRequest(**request_data)
            
            # Check if knowledge exists
            if request.knowledge_id not in self.knowledge_store:
                return UpdateKnowledgeMetadataResponse(
                    status="error: knowledge not found"
                )
            
            # Update metadata in vector store
            success = self.vector_store.update_metadata(request.knowledge_id, request.metadata)
            
            if success:
                # Update in-memory store
                self.knowledge_store[request.knowledge_id].metadata = request.metadata
                self.knowledge_store[request.knowledge_id].updated_at = datetime.now()
                
                logger.info(f"Updated metadata for knowledge {request.knowledge_id}")
                return UpdateKnowledgeMetadataResponse(status="success")
            else:
                return UpdateKnowledgeMetadataResponse(
                    status="error: failed to update vector store"
                )
                
        except Exception as e:
            logger.error(f"Error updating knowledge metadata: {e}")
            return UpdateKnowledgeMetadataResponse(
                status=f"error: {str(e)}"
            )
    
    def delete_knowledge(self, request_data: Dict[str, Any]) -> DeleteKnowledgeResponse:
        """Delete knowledge and all its chunks"""
        try:
            request = DeleteKnowledgeRequest(**request_data)
            
            # Check if knowledge exists
            if request.knowledge_id not in self.knowledge_store:
                return DeleteKnowledgeResponse(
                    status="error: knowledge not found"
                )
            
            # Delete from vector store
            success = self.vector_store.delete_by_knowledge_id(request.knowledge_id)
            
            if success:
                # Remove from in-memory store
                del self.knowledge_store[request.knowledge_id]
                
                logger.info(f"Deleted knowledge {request.knowledge_id}")
                return DeleteKnowledgeResponse(status="success")
            else:
                return DeleteKnowledgeResponse(
                    status="error: failed to delete from vector store"
                )
                
        except Exception as e:
            logger.error(f"Error deleting knowledge: {e}")
            return DeleteKnowledgeResponse(
                status=f"error: {str(e)}"
            )
    
    def search_knowledge(self, query: str, user_attributes, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant knowledge chunks based on user access"""
        try:
            # Build access filter
            access_filter = self.vector_store.build_access_filter(user_attributes)
            
            # Search vector store
            results = self.vector_store.search(
                query=query,
                n_results=n_results,
                where_filter=access_filter
            )
            
            # Additional filtering for complex access rules
            filtered_results = []
            for result in results:
                if self._check_user_access(result["metadata"], user_attributes):
                    filtered_results.append(result)
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
    
    def _check_user_access(self, chunk_metadata: Dict[str, Any], user_attributes) -> bool:
        """Check if user has access to a specific chunk based on metadata"""
        # Global knowledge is accessible to everyone
        if chunk_metadata.get("isGlobal", False):
            return True
        
        # Knowledge with no tenant restriction
        if not chunk_metadata.get("tenantId"):
            return True
        
        # Check tenant access
        chunk_tenant_id = chunk_metadata.get("tenantId")
        user_tenant_ids = [tenant.tenantId for tenant in user_attributes.userTenants]
        
        if chunk_tenant_id not in user_tenant_ids:
            return False
        
        # Check role access if specified
        chunk_role_ids = chunk_metadata.get("tenantRoleIds")
        if chunk_role_ids:
            # Parse comma-separated role IDs
            required_roles = chunk_role_ids.split(",") if isinstance(chunk_role_ids, str) else chunk_role_ids
            
            # Get user roles for this tenant
            user_roles = []
            for tenant in user_attributes.userTenants:
                if tenant.tenantId == chunk_tenant_id:
                    user_roles.append(tenant.tenantRole)
            
            # Check if user has any of the required roles
            if not any(role in user_roles for role in required_roles):
                return False
        
        return True
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        vector_stats = self.vector_store.get_collection_stats()
        return {
            "total_knowledge_items": len(self.knowledge_store),
            "vector_store_stats": vector_stats
        }
    
    def get_knowledge_chunks_by_id(self, knowledge_id: str, user_attributes) -> List[Dict[str, Any]]:
        """Get all chunks for a specific knowledge ID with user access check"""
        try:
            # Build access filter
            access_filter = self.vector_store.build_access_filter(user_attributes)
            
            # Add knowledge_id filter
            knowledge_filter = {"knowledge_id": knowledge_id}
            
            # Combine filters
            combined_filter = {"$and": [access_filter, knowledge_filter]}
            
            # Get chunks from vector store
            results = self.vector_store.collection.get(
                where=combined_filter,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results similar to search results
            formatted_results = []
            if results["ids"]:
                for i, chunk_id in enumerate(results["ids"]):
                    chunk_data = {
                        "id": chunk_id,
                        "content": results["documents"][i],
                        "metadata": results["metadatas"][i],
                        "relevance_score": 1.0  # Set high relevance for direct ID matches
                    }
                    
                    # Additional access check
                    if self._check_user_access(chunk_data["metadata"], user_attributes):
                        formatted_results.append(chunk_data)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error getting knowledge chunks by ID {knowledge_id}: {e}")
            return []


def setup_knowledge_service_handlers(mq_handler: MQHandler, knowledge_service: KnowledgeService):
    """Register knowledge service handlers with MQ system"""
    
    # Register legacy handlers
    mq_handler.register_handler("add_knowledge", knowledge_service.add_knowledge)
    mq_handler.register_handler("update_knowledge_metadata", knowledge_service.update_knowledge_metadata)
    mq_handler.register_handler("delete_knowledge", knowledge_service.delete_knowledge)
    
    # Register new topic-based handlers for the new message contract
    mq_handler.register_topic_handler("KNOWLEDGE_CREATE", knowledge_service.process_knowledge_create_message)
    mq_handler.register_topic_handler("KNOWLEDGE_UPDATE", knowledge_service.process_knowledge_update_message)
    mq_handler.register_topic_handler("KNOWLEDGE_DELETE", knowledge_service.process_knowledge_delete_message)
    
    logger.info("Knowledge service handlers (legacy and topic-based) registered with MQ system")