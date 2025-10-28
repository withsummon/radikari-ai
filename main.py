#!/usr/bin/env python3
"""
RAG Backend Microservice - Main Entry Point

A Python-based RAG microservice that:
1. Consumes MQ messages from external backend for knowledge operations
2. Provides HTTP endpoints for chat functionality with streaming responses

Usage:
- python main.py                    # Start HTTP API + MQ consumer (default)
- python main.py --mq-only         # Start only MQ consumer (no HTTP API)
- python -m src.mq_service         # Alternative way to start MQ-only service
"""

import os
import sys
import logging
import argparse
import asyncio
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def validate_environment():
    """Validate required environment variables"""
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file or environment configuration")
        sys.exit(1)


def start_http_api():
    """Start the HTTP API with MQ consumer"""
    try:
        import uvicorn
        from src.api import app
        
        # Get configuration from environment
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", "8000"))
        
        logger.info(f"Starting RAG Backend Microservice (HTTP + MQ) on {host}:{port}")
        
        # Start the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=os.getenv("LOG_LEVEL", "info").lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Failed to start HTTP API: {e}")
        sys.exit(1)


async def start_mq_only():
    """Start only the MQ consumer service"""
    try:
        from src.mq_service import PureMQService
        
        logger.info("Starting RAG Backend Microservice (MQ Only)")
        
        service = PureMQService()
        await service.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Failed to start MQ service: {e}")
        sys.exit(1)


def main():
    """Main entry point for the RAG Backend Microservice"""
    parser = argparse.ArgumentParser(description="RAG Backend Microservice")
    parser.add_argument(
        "--mq-only", 
        action="store_true", 
        help="Start only MQ consumer (no HTTP API)"
    )
    
    args = parser.parse_args()
    
    # Validate environment
    validate_environment()
    
    if args.mq_only:
        # Start only MQ consumer
        asyncio.run(start_mq_only())
    else:
        # Start HTTP API with MQ consumer (default)
        start_http_api()


if __name__ == "__main__":
    main()