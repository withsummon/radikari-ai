#!/usr/bin/env python3
"""
Test MQ Publisher - Simulates external backend sending knowledge operations
"""
import json
import asyncio
import aio_pika
from datetime import datetime
import uuid

class TestMQPublisher:
    def __init__(self, rabbitmq_url="amqp://admin:admin123@localhost:5672"):
        self.rabbitmq_url = rabbitmq_url
        self.connection = None
        self.channel = None
        self.queue_name = "knowledge_operations"

    async def connect(self):
        """Connect to RabbitMQ"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        
        # Declare queue (same as in MQ handler)
        await self.channel.declare_queue(self.queue_name, durable=True)
        print(f"✅ Connected to RabbitMQ and declared queue: {self.queue_name}")

    async def publish_message(self, operation, data):
        """Publish a message to the knowledge operations queue"""
        message_body = {
            "operation": operation,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "message_id": str(uuid.uuid4())
        }
        
        message = aio_pika.Message(
            json.dumps(message_body).encode(),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await self.channel.default_exchange.publish(
            message, routing_key=self.queue_name
        )
        
        print(f"📤 Published {operation} message: {message_body['message_id']}")
        return message_body

    async def test_add_knowledge(self):
        """Test adding knowledge"""
        data = {
            "content": "Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data without being explicitly programmed.",
            "metadata": {
                "tenantId": "company_a",
                "tenantRoleIds": ["admin", "editor"],
                "type": "ARTICLE",
                "isGlobal": False
            },
            "filetype": "text",
            "url": "https://example.com/ml-intro"
        }
        return await self.publish_message("add_knowledge", data)

    async def test_update_metadata(self, knowledge_id=None):
        """Test updating knowledge metadata"""
        if not knowledge_id:
            knowledge_id = "test_knowledge_" + str(uuid.uuid4())[:8]
            
        data = {
            "knowledge_id": knowledge_id,
            "metadata": {
                "tenantId": "company_a",
                "tenantRoleIds": ["admin", "editor", "viewer"],
                "type": "FILE",
                "isGlobal": True
            }
        }
        return await self.publish_message("update_knowledge_metadata", data)

    async def test_delete_knowledge(self, knowledge_id=None):
        """Test deleting knowledge"""
        if not knowledge_id:
            knowledge_id = "test_knowledge_" + str(uuid.uuid4())[:8]
            
        data = {
            "knowledge_id": knowledge_id
        }
        return await self.publish_message("delete_knowledge", data)

    async def run_test_suite(self):
        """Run a complete test suite"""
        print("🚀 Starting MQ Publisher Test Suite...")
        
        # Test 1: Add knowledge
        print("\n📝 Test 1: Adding knowledge...")
        add_result = await self.test_add_knowledge()
        await asyncio.sleep(2)  # Give time for processing
        
        # Test 2: Add more knowledge for variety
        print("\n📝 Test 2: Adding more knowledge...")
        data2 = {
            "content": "Deep learning uses neural networks with multiple layers to model and understand complex patterns in data.",
            "metadata": {
                "title": "Deep Learning Fundamentals",
                "source": "Neural Networks Guide",
                "tenant_id": "company_a",
                "tags": ["deep-learning", "neural-networks", "ai"],
                "category": "advanced"
            },
            "user_attributes": {
                "tenant_id": "company_a",
                "role": "user"
            }
        }
        await self.publish_message("add_knowledge", data2)
        await asyncio.sleep(2)
        
        # Test 3: Update metadata
        print("\n🔄 Test 3: Updating knowledge metadata...")
        await self.test_update_metadata()
        await asyncio.sleep(2)
        
        # Test 4: Delete knowledge
        print("\n🗑️ Test 4: Deleting knowledge...")
        await self.test_delete_knowledge()
        
        print("\n✅ Test suite completed!")

    async def close(self):
        """Close connection"""
        if self.connection:
            await self.connection.close()
            print("🔌 Disconnected from RabbitMQ")

async def main():
    publisher = TestMQPublisher()
    
    try:
        await publisher.connect()
        await publisher.run_test_suite()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await publisher.close()

if __name__ == "__main__":
    asyncio.run(main())