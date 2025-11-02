import openai
import logging
from typing import List, Dict, Any, AsyncGenerator
import json
from datetime import datetime
import os
import time
import tiktoken
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
        
        # Configuration - Optimized for faster streaming
        self.model = "gpt-3.5-turbo"  # Faster than GPT-4 for streaming
        self.max_context_chunks = 5
        self.max_tokens = 1000  # Reduced for faster response times
        
        # Initialize token encoder for tracking
        try:
            self.token_encoder = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # Fallback to cl100k_base encoding if model not found
            self.token_encoder = tiktoken.get_encoding("cl100k_base")
            
        logger.info(f"🤖 ChatService initialized with model: {self.model}, max_tokens: {self.max_tokens}")
        
    def _count_tokens(self, text: str) -> int:
        """Count tokens in a text string"""
        try:
            return len(self.token_encoder.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed: {e}, using character approximation")
            return len(text) // 4  # Rough approximation: 1 token ≈ 4 characters
            
    def _log_context_info(self, context: str, chunks: List[Dict[str, Any]], operation: str):
        """Log detailed context information"""
        context_tokens = self._count_tokens(context)
        logger.info(f"📝 {operation} - Context built:")
        logger.info(f"   📊 Chunks used: {len(chunks)}")
        logger.info(f"   🔤 Context length: {len(context)} chars, ~{context_tokens} tokens")
        logger.info(f"   📚 Knowledge sources: {[chunk.get('knowledge_id', 'unknown') for chunk in chunks[:3]]}{'...' if len(chunks) > 3 else ''}")
        
    def _log_ai_request(self, messages: List[Dict[str, str]], operation: str):
        """Log AI request details"""
        total_input_tokens = sum(self._count_tokens(msg.get('content', '')) for msg in messages)
        logger.info(f"🚀 {operation} - AI Request:")
        logger.info(f"   🔢 Messages count: {len(messages)}")
        logger.info(f"   📝 Input tokens: ~{total_input_tokens}")
        logger.info(f"   🎯 Model: {self.model}")
        logger.info(f"   ⚙️ Max tokens: {self.max_tokens}")
        
        # Log system prompt info
        system_msg = next((msg for msg in messages if msg.get('role') == 'system'), None)
        if system_msg:
            system_tokens = self._count_tokens(system_msg['content'])
            logger.info(f"   🎭 System prompt: {len(system_msg['content'])} chars, ~{system_tokens} tokens")
            
    def _log_ai_response(self, response_content: str, start_time: float, operation: str):
        """Log AI response details"""
        duration = time.time() - start_time
        response_tokens = self._count_tokens(response_content)
        tokens_per_second = response_tokens / duration if duration > 0 else 0
        
        logger.info(f"✅ {operation} - AI Response completed:")
        logger.info(f"   ⏱️ Duration: {duration:.2f}s")
        logger.info(f"   📝 Response tokens: ~{response_tokens}")
        logger.info(f"   🚀 Speed: {tokens_per_second:.1f} tokens/sec")
        logger.info(f"   📊 Response length: {len(response_content)} chars")
        
    def send_message(self, request: ChatRequest) -> ChatResponse:
        """Send a message and get a complete response with sources"""
        try:
            # Extract knowledge IDs from chat history
            knowledge_ids = self._extract_knowledge_ids_from_history(request.chathistory.messages)
            
            # Search for relevant knowledge (semantic search)
            relevant_chunks = self.knowledge_service.search_knowledge(
                query=request.message,
                user_attributes=request.user_attributes,
                n_results=self.max_context_chunks
            )
            
            # Get additional context from specific knowledge IDs mentioned in chat history
            knowledge_context_chunks = []
            if knowledge_ids:
                knowledge_context_chunks = self._get_knowledge_by_ids(knowledge_ids, request.user_attributes)
            
            # Combine both types of context
            all_chunks = relevant_chunks + knowledge_context_chunks
            
            # Remove duplicates based on chunk_id
            unique_chunks = self._deduplicate_chunks(all_chunks)
            
            # Build context from all relevant chunks
            context = self._build_context(unique_chunks)
            
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
            sources = self._create_sources(unique_chunks)
            
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
        operation_start = time.time()
        operation_id = f"stream_{int(operation_start * 1000)}"
        
        logger.info(f"🎬 Starting streaming chat operation: {operation_id}")
        logger.info(f"   👤 User query: '{request.message[:100]}{'...' if len(request.message) > 100 else ''}'")
        logger.info(f"   📜 Chat history length: {len(request.chathistory.messages)} messages")
        
        try:
            # Step 1: Extract knowledge IDs from chat history
            knowledge_search_start = time.time()
            knowledge_ids = self._extract_knowledge_ids_from_history(request.chathistory.messages)
            logger.info(f"🔍 Knowledge ID extraction: {len(knowledge_ids)} IDs found in {time.time() - knowledge_search_start:.3f}s")
            
            # Step 2: Search for relevant knowledge (semantic search)
            semantic_search_start = time.time()
            relevant_chunks = self.knowledge_service.search_knowledge(
                query=request.message,
                user_attributes=request.user_attributes,
                n_results=self.max_context_chunks
            )
            semantic_duration = time.time() - semantic_search_start
            logger.info(f"🔎 Semantic search completed: {len(relevant_chunks)} chunks in {semantic_duration:.3f}s")
            
            # Step 3: Get additional context from specific knowledge IDs mentioned in chat history
            context_search_start = time.time()
            knowledge_context_chunks = []
            if knowledge_ids:
                knowledge_context_chunks = self._get_knowledge_by_ids(knowledge_ids, request.user_attributes)
                logger.info(f"📚 Knowledge ID context: {len(knowledge_context_chunks)} chunks in {time.time() - context_search_start:.3f}s")
            
            # Step 4: Combine both types of context
            all_chunks = relevant_chunks + knowledge_context_chunks
            
            # Step 5: Remove duplicates based on chunk_id
            unique_chunks = self._deduplicate_chunks(all_chunks)
            logger.info(f"🔄 Deduplication: {len(all_chunks)} → {len(unique_chunks)} chunks")
            
            # Step 6: Build context from all relevant chunks
            context_build_start = time.time()
            context = self._build_context(unique_chunks)
            self._log_context_info(context, unique_chunks, f"STREAM-{operation_id}")
            
            # Step 7: Create system prompt with context
            system_prompt = self._create_system_prompt(context)
            
            # Step 8: Prepare messages for OpenAI
            messages = self._prepare_messages(request.chathistory.messages, request.message, system_prompt)
            self._log_ai_request(messages, f"STREAM-{operation_id}")
            
            # Step 9: Get streaming response from OpenAI - Optimized for speed
            ai_start_time = time.time()
            logger.info(f"🚀 Starting OpenAI streaming request...")
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for faster, more focused responses
                stream=True
            )
            
            # Step 10: Stream the response with buffer optimization
            buffer = ""
            buffer_size = 50  # Characters to buffer before sending
            total_response = ""
            chunk_count = 0
            first_token_time = None
            
            logger.info(f"📡 Starting response streaming...")
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    buffer += content
                    total_response += content
                    chunk_count += 1
                    
                    # Record time to first token
                    if first_token_time is None:
                        first_token_time = time.time()
                        logger.info(f"⚡ First token received in {first_token_time - ai_start_time:.3f}s")
                    
                    # Send buffer when it reaches the threshold or contains complete words
                    if len(buffer) >= buffer_size or content.endswith((' ', '\n', '.', '!', '?', ',')):
                        # Format as JSON for consistent streaming
                        stream_data = {
                            "type": "content",
                            "data": buffer
                        }
                        yield f"data: {json.dumps(stream_data)}\n\n"
                        buffer = ""
            
            # Send any remaining buffer content
            if buffer:
                stream_data = {
                    "type": "content",
                    "data": buffer
                }
                yield f"data: {json.dumps(stream_data)}\n\n"
            
            # Log AI response completion
            self._log_ai_response(total_response, ai_start_time, f"STREAM-{operation_id}")
            logger.info(f"📊 Streaming stats: {chunk_count} chunks processed")
            
            # Send sources at the end
            sources = self._create_sources(unique_chunks)
            sources_data = {
                "type": "sources",
                "data": [source.dict() for source in sources]
            }
            yield f"data: {json.dumps(sources_data)}\n\n"
            logger.info(f"📚 Sources sent: {len(sources)} sources")
            
            # Send end marker
            end_data = {"type": "end"}
            yield f"data: {json.dumps(end_data)}\n\n"
            
            # Log operation completion
            total_duration = time.time() - operation_start
            logger.info(f"🏁 Operation {operation_id} completed in {total_duration:.2f}s")
            logger.info(f"   📈 Performance summary:")
            logger.info(f"      🔍 Knowledge search: {semantic_duration:.3f}s")
            logger.info(f"      🤖 AI processing: {time.time() - ai_start_time:.3f}s")
            logger.info(f"      📊 Total chunks: {len(unique_chunks)}")
            logger.info(f"      📝 Response length: {len(total_response)} chars")
            
        except Exception as e:
            logger.error(f"❌ Error in streaming operation {operation_id}: {e}")
            logger.error(f"   ⏱️ Failed after {time.time() - operation_start:.2f}s")
            error_data = {
                "type": "error",
                "data": f"I apologize, but I encountered an error while processing your request: {str(e)}"
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    async def send_message_stream_with_attributes(self, request: StreamingChatRequest) -> AsyncGenerator[str, None]:
        """Send a message with user attributes filtering and get a streaming SSE response"""
        try:
            chat_start_time = time.time()
            operation_id = f"stream_chat_{int(chat_start_time * 1000)}"
            
            logger.info(f"🚀 STARTING STREAMING CHAT: {operation_id}")
            logger.info(f"=" * 80)
            logger.info(f"👤 User: {request.userAttributes.userId}")
            logger.info(f"🏢 User Tenants: {[t.tenantId for t in request.userAttributes.userTenants]}")
            logger.info(f"💬 User Message: '{request.message}'")
            logger.info(f"📚 Chat History Length: {len(request.chatHistory)} messages")
            
            # Extract knowledge IDs from chat history
            knowledge_ids = self._extract_knowledge_ids_from_history(request.chatHistory)
            if knowledge_ids:
                logger.info(f"🔗 Knowledge IDs from history: {knowledge_ids}")

            # Search for relevant knowledge with user attributes filtering (semantic search) - Async
            search_start = time.time()
            logger.info(f"🔍 PERFORMING SEMANTIC SEARCH...")
            relevant_chunks = await self.knowledge_service.search_knowledge(
                query=request.message,
                user_attributes=request.userAttributes,
                n_results=self.max_context_chunks
            )
            search_duration = time.time() - search_start
            logger.info(f"✅ Semantic search completed in {search_duration:.3f}s, found {len(relevant_chunks)} chunks")

            # Get additional context from specific knowledge IDs mentioned in chat history - Async
            knowledge_context_chunks = []
            if knowledge_ids:
                context_start = time.time()
                logger.info(f"📖 FETCHING KNOWLEDGE BY IDs...")
                knowledge_context_chunks = await self._get_knowledge_by_ids_async(knowledge_ids, request.userAttributes)
                context_duration = time.time() - context_start
                logger.info(f"✅ Knowledge fetch completed in {context_duration:.3f}s, found {len(knowledge_context_chunks)} chunks")

            # Combine both types of context
            all_chunks = relevant_chunks + knowledge_context_chunks
            logger.info(f"🔗 Combined chunks: {len(relevant_chunks)} semantic + {len(knowledge_context_chunks)} from history = {len(all_chunks)} total")

            # Remove duplicates based on chunk_id
            unique_chunks = self._deduplicate_chunks(all_chunks)
            logger.info(f"🎯 After deduplication: {len(unique_chunks)} unique chunks")

            # Build context from all relevant chunks
            context_start = time.time()
            context = self._build_context(unique_chunks)
            context_duration = time.time() - context_start
            
            # Log detailed context information
            self._log_context_info(context, unique_chunks, operation_id)
            logger.info(f"📝 FULL CONTEXT CONTENT:")
            logger.info(f"=" * 60)
            logger.info(context)
            logger.info(f"=" * 60)

            # Create system prompt with context
            system_prompt = self._create_system_prompt(context)
            system_tokens = self._count_tokens(system_prompt)
            logger.info(f"🎭 SYSTEM PROMPT ({system_tokens} tokens):")
            logger.info(f"=" * 60)
            logger.info(system_prompt)
            logger.info(f"=" * 60)

            # Prepare messages for OpenAI
            messages = self._prepare_messages_from_list(request.chatHistory, request.message, system_prompt)
            
            # Log AI request details
            self._log_ai_request(messages, operation_id)
            logger.info(f"📤 FULL AI REQUEST MESSAGES:")
            logger.info(f"=" * 60)
            for i, msg in enumerate(messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                tokens = self._count_tokens(content)
                logger.info(f"Message {i+1} ({role.upper()}) - {tokens} tokens:")
                logger.info(f"   {content}")
                if i < len(messages) - 1:
                    logger.info(f"   {'-' * 40}")
            logger.info(f"=" * 60)

            # Get streaming response from OpenAI - Optimized for speed
            ai_start_time = time.time()
            logger.info(f"🤖 SENDING REQUEST TO OPENAI...")
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for faster, more focused responses
                stream=True
            )

            # Stream the response in SSE format with buffer optimization
            buffer = ""
            buffer_size = 50  # Characters to buffer before sending
            full_response = ""  # Track full response for logging
            
            logger.info(f"📡 STREAMING AI RESPONSE...")
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    buffer += content
                    full_response += content
                    
                    # Send buffer when it reaches the threshold or contains complete words
                    if len(buffer) >= buffer_size or content.endswith((' ', '\n', '.', '!', '?', ',')):
                        # Format as SSE event
                        yield f"event: message\n"
                        yield f"data: {json.dumps({'type': 'content', 'content': buffer})}\n\n"
                        buffer = ""

            # Send any remaining buffer content
            if buffer:
                yield f"event: message\n"
                yield f"data: {json.dumps({'type': 'content', 'content': buffer})}\n\n"
                
            # Log AI response details
            self._log_ai_response(full_response, ai_start_time, operation_id)
            logger.info(f"📥 FULL AI RESPONSE:")
            logger.info(f"=" * 60)
            logger.info(full_response)
            logger.info(f"=" * 60)

            # Send sources at the end
            sources = self._create_sources(unique_chunks)
            # Filter sources based on user access
            accessible_sources = self._check_user_access_to_sources(sources, request.userAttributes)
            
            logger.info(f"📚 SOURCES ({len(accessible_sources)} accessible out of {len(sources)} total):")
            for i, source in enumerate(accessible_sources):
                logger.info(f"   Source {i+1}: {source.knowledge_id} (Score: {source.relevance_score:.4f})")

            yield f"event: sources\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': [source.dict() for source in accessible_sources]})}\n\n"

            # Send end marker
            yield f"event: end\n"
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
            total_duration = time.time() - chat_start_time
            logger.info(f"🏁 STREAMING CHAT COMPLETED: {operation_id}")
            logger.info(f"   ⏱️ Total Duration: {total_duration:.3f}s")
            logger.info(f"   🔍 Search: {search_duration:.3f}s")
            logger.info(f"   📝 Context: {context_duration:.3f}s") 
            logger.info(f"   🤖 AI Response: {time.time() - ai_start_time:.3f}s")
            logger.info(f"=" * 80)

        except Exception as e:
            logger.error(f"❌ ERROR in {operation_id}: {e}")
            logger.error(f"   Full error details:", exc_info=True)
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
    
    def _extract_knowledge_ids_from_history(self, chat_history: List[ChatMessage]) -> List[str]:
        """Extract knowledge IDs from chat history messages"""
        knowledge_ids = []
        for message in chat_history:
            if hasattr(message, 'knowledge_id') and message.knowledge_id:
                knowledge_ids.append(message.knowledge_id)
        return list(set(knowledge_ids))  # Remove duplicates
    
    def _get_knowledge_by_ids(self, knowledge_ids: List[str], user_attributes: UserAttributes) -> List[Dict[str, Any]]:
        """Retrieve knowledge chunks by specific knowledge IDs"""
        all_chunks = []
        for knowledge_id in knowledge_ids:
            try:
                # Get chunks for this specific knowledge ID
                chunks = self.knowledge_service.get_knowledge_chunks_by_id(knowledge_id, user_attributes)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Could not retrieve knowledge for ID {knowledge_id}: {e}")
        return all_chunks

    async def _get_knowledge_by_ids_async(self, knowledge_ids: List[str], user_attributes: UserAttributes) -> List[Dict[str, Any]]:
        """Retrieve knowledge chunks by specific knowledge IDs - Async version for better performance"""
        all_chunks = []
        for knowledge_id in knowledge_ids:
            try:
                # Get chunks for this specific knowledge ID - Async
                chunks = await self.knowledge_service.get_knowledge_chunks_by_id(knowledge_id, user_attributes)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning(f"Could not retrieve knowledge for ID {knowledge_id}: {e}")
        return all_chunks
    
    def _deduplicate_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate chunks based on chunk_id"""
        seen_ids = set()
        unique_chunks = []
        for chunk in chunks:
            chunk_id = chunk.get("id")
            if chunk_id and chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                unique_chunks.append(chunk)
        return unique_chunks