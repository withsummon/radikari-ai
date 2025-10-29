#!/usr/bin/env python3
"""
Test MQ Knowledge Operations - Tests knowledge ingestion via RabbitMQ messages
"""
import json
import pika
import uuid
from datetime import datetime

def test_knowledge_create_message():
    """Test sending a KNOWLEDGE_CREATE message via RabbitMQ"""
    
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='localhost',
            port=5672,
            virtual_host='/',
            credentials=pika.PlainCredentials('admin', 'admin123')
        )
    )
    channel = connection.channel()
    
    # Declare the queue
    channel.queue_declare(queue='knowledge_operations', durable=True)
    
    # Create test message
    knowledge_id = str(uuid.uuid4())
    message = {
        "metadata": {
            "knowledgeId": knowledge_id,
            "type": "ARTICLE",
            "access": "TENANT",
            "tenantId": "test-tenant",
            "accessUserIds": ["test-user"]
        },
        "content": "This is a test document for RAG testing. It contains information about testing procedures and methodologies.",
        "fileType": "pdf",
        "fileUrls": []
    }
    
    # Send message
    channel.basic_publish(
        exchange='',
        routing_key='knowledge_operations',
        body=json.dumps({
            "operation": "KNOWLEDGE_CREATE",
            "data": message
        }),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
            correlation_id=str(uuid.uuid4()),
            timestamp=int(datetime.now().timestamp())
        )
    )
    
    print(f"✅ Sent KNOWLEDGE_CREATE message for knowledge ID: {knowledge_id}")
    print(f"📄 Content: {message['content'][:100]}...")
    
    connection.close()
    return knowledge_id

def test_knowledge_delete_message(knowledge_id):
    """Test sending a KNOWLEDGE_DELETE message via RabbitMQ"""
    
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='localhost',
            port=5672,
            virtual_host='/',
            credentials=pika.PlainCredentials('admin', 'admin123')
        )
    )
    channel = connection.channel()
    
    # Declare the queue
    channel.queue_declare(queue='knowledge_operations', durable=True)
    
    # Create delete message
    message = {
        "knowledgeId": knowledge_id
    }
    
    # Send message
    channel.basic_publish(
        exchange='',
        routing_key='knowledge_operations',
        body=json.dumps({
            "operation": "KNOWLEDGE_DELETE",
            "data": message
        }),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
            correlation_id=str(uuid.uuid4()),
            timestamp=int(datetime.now().timestamp())
        )
    )
    
    print(f"✅ Sent KNOWLEDGE_DELETE message for knowledge ID: {knowledge_id}")
    
    connection.close()

if __name__ == "__main__":
    print("🧪 Testing MQ Knowledge Operations")
    print("=" * 50)
    
    # Test knowledge creation
    print("\n1. Testing Knowledge Creation via MQ...")
    knowledge_id = test_knowledge_create_message()
    
    # Wait for user input to test deletion
    input("\n⏸️  Press Enter to test knowledge deletion...")
    
    # Test knowledge deletion
    print("\n2. Testing Knowledge Deletion via MQ...")
    test_knowledge_delete_message(knowledge_id)
    
    print("\n✅ MQ Knowledge Operations test completed!")