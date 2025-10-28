import openai
import logging
from typing import List, Dict, Any, AsyncGenerator
import json
from datetime import datetime
import os
from dotenv import load_dotenv

from .models import (
    ChatRequest, ChatResponse, ChatMessage, Source, UserAttributes, StreamingChatRequest
)
from .knowledge_service import KnowledgeService

load_dotenv()

logger = logging.getLogger(__name__)


class ChatService:
    """Service for handling RAG-based chat interactions"""
    
    def __init__(self, knowledge_service: KnowledgeService):
        self.knowledge_service = knowledge_service
        
        # Initialize OpenAI client
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        openai.api_key = openai_api_key
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Configuration
        self.model = "gpt-4-turbo-preview"
        self.max_context_chunks = 5
        self.max_tokens = 2000
        
    def send_message(self, request: ChatRequest) -> ChatResponse:
        """Send a message and get a complete response with sources"""
        try:
            # Search for relevant knowledge
            relevant_chunks = self.knowledge_service.search_knowledge(
                query=request.message,
                user_attributes=request.user_attributes,
                n_results=self.max_context_chunks
            )
            
            # Build context from relevant chunks
            context = self._build_context(relevant_chunks)
            
            # Create system prompt with context
            system_prompt = self._create_system_prompt(context)
            
            # Prepare messages for OpenAI
            messages = self._prepare_messages(request.chathistory.messages, request.message, system_prompt)
            
            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            
            # Extract response content
            response_content = response.choices[0].message.content
            
            # Create sources
            sources = self._create_sources(relevant_chunks)
            
            return ChatResponse(
                response=response_content,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"Error in send_message: {e}")
            return ChatResponse(
                response=f"I apologize, but I encountered an error while processing your request: {str(e)}",
                sources=[]
            )
    
    async def send_message_stream(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """Send a message and get a streaming response"""
        try:
            # Search for relevant knowledge
            relevant_chunks = self.knowledge_service.search_knowledge(
                query=request.message,
                user_attributes=request.user_attributes,
                n_results=self.max_context_chunks
            )
            
            # Build context from relevant chunks
            context = self._build_context(relevant_chunks)
            
            # Create system prompt with context
            system_prompt = self._create_system_prompt(context)
            
            # Prepare messages for OpenAI
            messages = self._prepare_messages(request.chathistory.messages, request.message, system_prompt)
            
            # Get streaming response from OpenAI
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7,
                stream=True
            )
            
            # Stream the response
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    
                    # Format as JSON for consistent streaming
                    stream_data = {
                        "type": "content",
                        "data": content
                    }
                    yield f"data: {json.dumps(stream_data)}\n\n"
            
            # Send sources at the end
            sources = self._create_sources(relevant_chunks)
            sources_data = {
                "type": "sources",
                "data": [source.dict() for source in sources]
            }
            yield f"data: {json.dumps(sources_data)}\n\n"
            
            # Send end marker
            end_data = {"type": "end"}
            yield f"data: {json.dumps(end_data)}\n\n"
            
        except Exception as e:
            logger.error(f"Error in send_message_stream: {e}")
            error_data = {
                "type": "error",
                "data": f"I apologize, but I encountered an error while processing your request: {str(e)}"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    async def send_message_stream_with_attributes(self, request: StreamingChatRequest) -> AsyncGenerator[str, None]:
        """Send a message with user attributes filtering and get a streaming SSE response"""
        try:
            # Search for relevant knowledge with user attributes filtering
            relevant_chunks = self.knowledge_service.search_knowledge(
                query=request.message,
                user_attributes=request.userAttributes,
                n_results=self.max_context_chunks
            )
            
            # Build context from relevant chunks
            context = self._build_context(relevant_chunks)
            
            # Create system prompt with context
            system_prompt = self._create_system_prompt(context)
            
            # Prepare messages for OpenAI
            messages = self._prepare_messages_from_list(request.chatHistory, request.message, system_prompt)
            
            # Get streaming response from OpenAI
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7,
                stream=True
            )
            
            # Stream the response in SSE format
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    
                    # Format as SSE event
                    yield f"event: message\n"
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
            
            # Send sources at the end
            sources = self._create_sources(relevant_chunks)
            # Filter sources based on user access
            accessible_sources = self._check_user_access_to_sources(sources, request.userAttributes)
            
            yield f"event: sources\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': [source.dict() for source in accessible_sources]})}\n\n"
            
            # Send end marker
            yield f"event: end\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in send_message_stream_with_attributes: {e}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'type': 'error', 'message': f'I apologize, but I encountered an error while processing your request: {str(e)}'})}\n\n"
    
    def _prepare_messages_from_list(self, chat_history: List[ChatMessage], new_message: str, system_prompt: str) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI API from a list of ChatMessage objects"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history (limit to recent messages to stay within token limits)
        recent_messages = chat_history[-10:] if len(chat_history) > 10 else chat_history
        
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add new user message
        messages.append({
            "role": "user",
            "content": new_message
        })
        
        return messages

    def _build_context(self, relevant_chunks: List[Dict[str, Any]]) -> str:
        """Build context string from relevant knowledge chunks"""
        if not relevant_chunks:
            return "No relevant context found."
        
        context_parts = []
        for i, chunk in enumerate(relevant_chunks, 1):
            context_parts.append(f"Context {i}:\n{chunk['content']}\n")
        
        return "\n".join(context_parts)
    
    def _create_system_prompt(self, context: str) -> str:
        """Create system prompt with context"""
        return f"""You are a helpful AI assistant with access to a knowledge base. Use the provided context to answer user questions accurately and helpfully.

Context from knowledge base:
{context}

Instructions:
1. Use the provided context to answer questions when relevant
2. If the context doesn't contain relevant information, say so clearly
3. Always be helpful and provide accurate information
4. Cite specific parts of the context when using them in your response
5. If you're unsure about something, acknowledge the uncertainty
6. Keep responses concise but comprehensive

Remember: Only use information from the provided context or your general knowledge. Do not make up facts."""
    
    def _prepare_messages(self, chat_history: List[ChatMessage], new_message: str, system_prompt: str) -> List[Dict[str, str]]:
        """Prepare messages for OpenAI API"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history (limit to recent messages to stay within token limits)
        recent_messages = chat_history[-10:] if len(chat_history) > 10 else chat_history
        
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add new user message
        messages.append({
            "role": "user",
            "content": new_message
        })
        
        return messages
    
    def _create_sources(self, relevant_chunks: List[Dict[str, Any]]) -> List[Source]:
        """Create source objects from relevant chunks"""
        sources = []
        
        for chunk in relevant_chunks:
            metadata = chunk["metadata"]
            
            # Reconstruct KnowledgeMetadata from flat metadata
            knowledge_metadata = {
                "tenantId": metadata.get("tenantId"),
                "tenantRoleIds": metadata.get("tenantRoleIds", "").split(",") if metadata.get("tenantRoleIds") else None,
                "type": metadata.get("type", "ARTICLE"),
                "isGlobal": metadata.get("isGlobal", False)
            }
            
            source = Source(
                knowledge_id=metadata["knowledge_id"],
                chunk_id=chunk["id"],
                content=chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"],
                metadata=knowledge_metadata,
                relevance_score=chunk["relevance_score"]
            )
            sources.append(source)
        
        return sources
    
    def _check_user_access_to_sources(self, sources: List[Source], user_attributes: UserAttributes) -> List[Source]:
        """Filter sources based on user access permissions"""
        accessible_sources = []
        
        for source in sources:
            if self.knowledge_service._check_user_access(source.metadata.dict(), user_attributes):
                accessible_sources.append(source)
        
        return accessible_sources