#!/usr/bin/env python3
"""
Radikari AI - Headless Offline Worker

A Python-based worker that consumes MQ messages from external backend for knowledge operations.
This service runs as a headless worker without any HTTP API endpoints.

Usage:
- python main.py         # Start MQ consumer worker
"""

import os
import sys
import logging
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
    required_vars = ["GOOGLE_API_KEY", "QDRANT_URL"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please check your .env file or environment configuration")
        sys.exit(1)


async def start_mq_worker():
    """Start the MQ consumer worker"""
    try:
        from src.mq_service import PureMQService
        
        logger.info("Starting Radikari AI Worker (MQ Only)")
        
        service = PureMQService()
        await service.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Failed to start MQ worker: {e}")
        sys.exit(1)


def main():
    """Main entry point for the Radikari AI Worker"""
    # Validate environment
    validate_environment()
    
    # Start MQ worker
    asyncio.run(start_mq_worker())


if __name__ == "__main__":
    main()