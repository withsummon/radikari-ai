#!/usr/bin/env python3
"""
Simple MQ connectivity test
"""

import os
import pika
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_mq_connectivity():
    """Test MQ connectivity"""
    print("🔌 Testing MQ Connectivity")
    print("=" * 50)
    
    # Get MQ URL from environment
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    
    if not rabbitmq_url:
        print("❌ RABBITMQ_URL not found in environment")
        return False
    
    print(f"📡 Testing connection to: {rabbitmq_url}")
    
    try:
        # Parse URL to hide credentials in logs
        parsed = urlparse(rabbitmq_url)
        safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}{parsed.path}"
        print(f"🏠 Host: {safe_url}")
        
        # Test connection
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        print("✅ Connection established successfully")
        
        # Test channel
        channel = connection.channel()
        print("✅ Channel created successfully")
        
        # Get server properties
        if hasattr(connection, '_impl') and hasattr(connection._impl, 'server_properties'):
            server_props = connection._impl.server_properties
            if b'version' in server_props:
                version = server_props[b'version'].decode('utf-8')
                print(f"🐰 RabbitMQ version: {version}")
        
        # Close connection
        connection.close()
        print("✅ Connection closed cleanly")
        
        return True
        
    except pika.exceptions.AMQPConnectionError as e:
        print(f"❌ AMQP Connection Error: {e}")
        print("💡 Check if RabbitMQ server is running and accessible")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("💡 Check your RABBITMQ_URL configuration")
        return False

def check_env_config():
    """Check environment configuration"""
    print("\n📋 Environment Configuration")
    print("=" * 50)
    
    rabbitmq_url = os.getenv('RABBITMQ_URL')
    if rabbitmq_url:
        # Parse and display safe info
        parsed = urlparse(rabbitmq_url)
        print(f"✅ RABBITMQ_URL configured")
        print(f"   Scheme: {parsed.scheme}")
        print(f"   Host: {parsed.hostname}")
        print(f"   Port: {parsed.port}")
        print(f"   Path: {parsed.path}")
        print(f"   Username: {'***' if parsed.username else 'None'}")
        print(f"   Password: {'***' if parsed.password else 'None'}")
    else:
        print("❌ RABBITMQ_URL not configured")
    
    return rabbitmq_url is not None

if __name__ == "__main__":
    print("🚀 MQ Connectivity Test")
    print("=" * 60)
    
    # Check configuration
    config_ok = check_env_config()
    
    if config_ok:
        # Test connectivity
        connectivity_ok = test_mq_connectivity()
        
        # Summary
        print("\n📊 Test Results")
        print("=" * 50)
        print(f"Configuration: {'✅ OK' if config_ok else '❌ MISSING'}")
        print(f"Connectivity: {'✅ CONNECTED' if connectivity_ok else '❌ FAILED'}")
        
        if not connectivity_ok:
            print("\n🔧 Troubleshooting Tips:")
            print("1. Verify RabbitMQ server is running")
            print("2. Check network connectivity to the host")
            print("3. Verify credentials are correct")
            print("4. Check firewall settings")
    else:
        print("\n❌ Cannot test connectivity without RABBITMQ_URL configuration")