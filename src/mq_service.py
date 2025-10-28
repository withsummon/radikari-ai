"""
Pure MQ Service - Standalone service that only consumes messages from external backend
This service runs independently and processes knowledge operations via MQ without HTTP API
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from .vector_store import ChromaVectorStore
from .knowledge_service import KnowledgeService, setup_knowledge_service_handlers
from .mq_handler import MQHandler, start_mq_consumer_thread

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PureMQService:
    """Pure MQ service that only consumes messages from external backend"""
    
    def __init__(self):
        self.vector_store = None
        self.knowledge_service = None
        self.mq_handler = None
        self.running = False
    
    async def initialize(self):
        """Initialize all services"""
        try:
            logger.info("Initializing Pure MQ Service...")
            
            # Initialize vector store
            self.vector_store = ChromaVectorStore()
            logger.info("Vector store initialized")
            
            # Initialize knowledge service
            self.knowledge_service = KnowledgeService(self.vector_store)
            logger.info("Knowledge service initialized")
            
            # Initialize MQ handler
            self.mq_handler = MQHandler()
            await self.mq_handler.connect()
            logger.info("MQ handler connected")
            
            # Setup knowledge service handlers for MQ consumption
            setup_knowledge_service_handlers(self.mq_handler, self.knowledge_service)
            logger.info("Knowledge service MQ handlers registered")
            
            logger.info("Pure MQ Service initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pure MQ Service: {e}")
            raise
    
    async def start(self):
        """Start the MQ consumer service"""
        try:
            await self.initialize()
            
            logger.info("Starting MQ consumer - ready to receive messages from external backend...")
            
            # Start MQ consumer thread
            start_mq_consumer_thread(self.mq_handler)
            self.running = True
            
            logger.info("Pure MQ Service started successfully - listening for messages")
            
            # Keep the service running
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            await self.stop()
        except Exception as e:
            logger.error(f"Error in Pure MQ Service: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the MQ service"""
        logger.info("Stopping Pure MQ Service...")
        
        self.running = False
        
        try:
            if self.mq_handler:
                await self.mq_handler.close()
                logger.info("MQ handler closed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Pure MQ Service stopped")


async def main():
    """Main entry point for pure MQ service"""
    # Validate required environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file")
        return
    
    # Create and start the service
    service = PureMQService()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())