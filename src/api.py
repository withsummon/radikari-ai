from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import traceback
from contextlib import asynccontextmanager

from .models import ChatRequest, ChatResponse, StreamingChatRequest
from .chat_service import ChatService
from .knowledge_service import KnowledgeService, setup_knowledge_service_handlers
from .vector_store import ChromaVectorStore
from .mq_handler import MQHandler, start_mq_consumer_thread

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Global variables for services
vector_store = None
knowledge_service = None
chat_service = None
mq_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global vector_store, knowledge_service, chat_service, mq_handler
    
    # Startup
    logger.info("=== Starting RAG Backend Microservice ===")
    
    try:
        # Initialize vector store
        logger.info("Step 1/5: Initializing ChromaDB vector store...")
        vector_store = ChromaVectorStore()
        logger.info("✓ Vector store initialized successfully")
        
        # Initialize knowledge service
        logger.info("Step 2/5: Initializing knowledge service...")
        knowledge_service = KnowledgeService(vector_store)
        logger.info("✓ Knowledge service initialized successfully")
        
        # Initialize chat service
        logger.info("Step 3/5: Initializing chat service...")
        chat_service = ChatService(knowledge_service)
        logger.info("✓ Chat service initialized successfully")
        
        # Initialize MQ handler for consuming messages from external backend
        logger.info("Step 4/5: Initializing MQ handler...")
        mq_handler = MQHandler()
        mq_handler.connect()
        logger.info("✓ MQ handler connected successfully")
        
        # Setup knowledge service handlers for MQ consumption
        logger.info("Step 5/5: Setting up knowledge service handlers...")
        setup_knowledge_service_handlers(mq_handler, knowledge_service)
        
        # Start MQ consumer thread
        logger.info("Starting MQ consumer thread...")
        start_mq_consumer_thread(mq_handler)
        logger.info("✓ MQ consumer thread started successfully")
        
        logger.info("=== RAG Backend Microservice Started Successfully ===")
        
    except Exception as e:
        logger.error(f"✗ Failed to start RAG Backend Microservice: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise
    
    yield
    
    # Shutdown
    logger.info("=== Shutting down RAG Backend Microservice ===")
    try:
        if mq_handler:
            logger.info("Closing MQ connection...")
            mq_handler.disconnect()
            logger.info("✓ MQ connection closed")
    except Exception as e:
        logger.error(f"✗ Error during shutdown: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
    
    logger.info("=== RAG Backend Microservice Shutdown Complete ===")


app = FastAPI(
    title="RAG Backend Microservice",
    description="A Python-based RAG microservice that consumes MQ messages for knowledge management and provides HTTP chat endpoints",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        stats = knowledge_service.get_knowledge_stats() if knowledge_service else {}
        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # You might want to use actual timestamp
            "services": {
                "vector_store": "running" if vector_store else "not_initialized",
                "knowledge_service": "running" if knowledge_service else "not_initialized",
                "chat_service": "running" if chat_service else "not_initialized",
                "mq_handler": "running" if mq_handler and mq_handler.is_running else "not_running"
            },
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Chat endpoints
@app.post("/chat/send", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a chat message and get a complete response with sources"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="Chat service not initialized")
        
        response = chat_service.send_message(request)
        return response
        
    except Exception as e:
        logger.error(f"Error in send_message endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def send_message_stream(request: ChatRequest):
    """Send a chat message and get a streaming response"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="Chat service not initialized")
        
        return StreamingResponse(
            chat_service.send_message_stream(request),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in send_message_stream endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream-sse")
async def send_message_stream_sse(request: StreamingChatRequest):
    """Send a chat message with user attributes filtering and get a streaming SSE response"""
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="Chat service not initialized")
        
        return StreamingResponse(
            chat_service.send_message_stream_with_attributes(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in send_message_stream_sse endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge operations are now handled purely via MQ consumption
# No HTTP endpoints needed - external backend sends MQ messages directly


# Statistics endpoint
@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        if not knowledge_service:
            raise HTTPException(status_code=500, detail="Knowledge service not initialized")
        
        stats = knowledge_service.get_knowledge_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error in get_stats endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )