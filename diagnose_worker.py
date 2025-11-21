#!/usr/bin/env python3
"""
Comprehensive diagnostic script for the Radikari AI Worker
This script helps identify and troubleshoot timeout issues
"""

import os
import sys
import time
from dotenv import load_dotenv

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

load_dotenv()

import pika
from qdrant_client import QdrantClient
import google.generativeai as genai

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_success(message):
    """Print success message"""
    print(f"✓ {message}")

def print_error(message):
    """Print error message"""
    print(f"✗ {message}")

def print_info(message):
    """Print info message"""
    print(f"ℹ {message}")

def check_environment_variables():
    """Check all required environment variables"""
    print_header("ENVIRONMENT VARIABLES CHECK")
    
    required_vars = {
        "GOOGLE_API_KEY": "Google Generative AI API key",
        "QDRANT_URL": "Qdrant vector database URL", 
        "QDRANT_API_KEY": "Qdrant API key (if required)",
        "RABBITMQ_URL": "RabbitMQ connection URL"
    }
    
    all_good = True
    
    print("Required Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if "API_KEY" in var:
                print_success(f"{var}: {'*' * 8}...{value[-4:]} ({description})")
            else:
                print_success(f"{var}: {value} ({description})")
        else:
            print_error(f"{var}: MISSING ({description})")
            all_good = False
    
    return all_good

def check_rabbitmq_connection():
    """Test RabbitMQ connection with detailed diagnostics"""
    print_header("RABBITMQ CONNECTION TEST")
    
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    if not rabbitmq_url:
        print_error("RABBITMQ_URL not configured")
        return False
    
    print_info(f"Testing connection to: {rabbitmq_url}")
    
    # Validate URL format
    if not rabbitmq_url.startswith('amqp://'):
        print_error("RabbitMQ URL should start with 'amqp://' protocol")
        print_info("Current URL format may be incorrect")
        return False
    
    try:
        start_time = time.time()
        
        # Configure connection parameters with timeouts
        parameters = pika.URLParameters(rabbitmq_url)
        parameters.socket_timeout = 10
        parameters.connection_attempts = 2
        parameters.retry_delay = 3
        
        print_info("Attempting connection...")
        connection = pika.BlockingConnection(parameters)
        
        connect_time = time.time() - start_time
        print_success(f"Connection established in {connect_time:.2f}s")
        
        # Test channel creation
        print_info("Testing channel creation...")
        channel = connection.channel()
        print_success("Channel created successfully")
        
        connection.close()
        print_success("Connection closed properly")
        
        return True
        
    except pika.exceptions.AMQPConnectionError as e:
        print_error(f"AMQP Connection Error: {e}")
        print_info("Possible causes:")
        print_info("  - RabbitMQ service is not running")
        print_info("  - Network connectivity issues")
        print_info("  - Incorrect URL or credentials")
        return False
    except Exception as e:
        print_error(f"Unexpected Error: {type(e).__name__}: {e}")
        print_info("This may indicate a configuration or network issue")
        return False

def check_qdrant_connection():
    """Test Qdrant connection with detailed diagnostics"""
    print_header("QDRANT CONNECTION TEST")
    
    qdrant_url = os.getenv('QDRANT_URL')
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    
    if not qdrant_url:
        print_error("QDRANT_URL not configured")
        return False
    
    print_info(f"Testing connection to: {qdrant_url}")
    print_info(f"API Key: {'configured' if qdrant_api_key else 'not configured'}")
    
    try:
        start_time = time.time()
        
        # Test connection with timeout
        client = QdrantClient(
            url=qdrant_url, 
            api_key=qdrant_api_key, 
            timeout=15
        )
        
        # Test basic operation
        print_info("Testing collection access...")
        collections = client.get_collections()
        connect_time = time.time() - start_time
        
        print_success(f"Connection successful in {connect_time:.2f}s")
        print_success(f"Found {len(collections.collections)} collections")
        
        return True
        
    except Exception as e:
        print_error(f"Connection failed: {type(e).__name__}: {e}")
        print_info("Possible causes:")
        print_info("  - Qdrant service is not running")
        print_info("  - Network connectivity issues")
        print_info("  - Invalid API key or URL")
        return False

def check_google_api_connection():
    """Test Google API connection"""
    print_header("GOOGLE API CONNECTION TEST")
    
    google_api_key = os.getenv('GOOGLE_API_KEY')
    
    if not google_api_key:
        print_error("GOOGLE_API_KEY not configured")
        return False
    
    print_info("API key is configured")
    
    try:
        start_time = time.time()
        
        genai.configure(api_key=google_api_key)
        
        # Test embedding generation
        print_info("Testing embedding generation...")
        result = genai.embed_content(
            model="gemini-embedding-001",
            content="test diagnostic",
            task_type="retrieval_document"
        )
        
        connect_time = time.time() - start_time
        print_success(f"API connection successful in {connect_time:.2f}s")
        print_success(f"Generated embedding with {len(result['embedding'])} dimensions")
        
        return True
        
    except Exception as e:
        print_error(f"API connection failed: {type(e).__name__}: {e}")
        print_info("Possible causes:")
        print_info("  - Invalid or expired API key")
        print_info("  - Google GenAI API not enabled")
        print_info("  - Network connectivity issues")
        return False

def main():
    """Run comprehensive diagnostics"""
    print_header("RAIDKARI AI WORKER DIAGNOSTICS")
    print("This script will test all service connections and identify issues")
    
    results = {}
    
    # Check environment
    results['Environment'] = check_environment_variables()
    
    # Test services
    results['RabbitMQ'] = check_rabbitmq_connection()
    results['Qdrant'] = check_qdrant_connection()
    results['Google API'] = check_google_api_connection()
    
    # Summary
    print_header("DIAGNOSTIC SUMMARY")
    
    for service, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{service:12}: {status}")
    
    # Recommendations
    print_header("RECOMMENDATIONS")
    
    all_passed = all(results.values())
    
    if all_passed:
        print_success("All services are working correctly!")
        print_info("You should be able to run the worker without timeout issues.")
        return 0
    else:
        print_error("Some services are not accessible. This is likely causing the timeout.")
        
        print("\nTo fix the timeout issue:")
        print("1. Fix any failed service connections above")
        print("2. Ensure all services are running and accessible")
        print("3. Verify environment variables are correct")
        print("4. Check network connectivity and firewall settings")
        
        if not results['RabbitMQ']:
            print("\nRABBITMQ SPECIFIC FIXES:")
            print("- Ensure URL format: amqp://username:password@host:port")
            print("- Check that RabbitMQ service is running")
            print("- Verify credentials and network access")
        
        if not results['Qdrant']:
            print("\nQDRANT SPECIFIC FIXES:")
            print("- Ensure QDRANT_URL is correct and accessible")
            print("- Check API key if required")
            print("- Verify Qdrant service is running")
        
        if not results['Google API']:
            print("\nGOOGLE API SPECIFIC FIXES:")
            print("- Verify API key is valid and active")
            print("- Ensure Google GenAI API is enabled")
            print("- Check network connectivity to Google services")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())