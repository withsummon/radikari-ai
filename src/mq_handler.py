import pika
import json
import logging
import asyncio
from typing import Callable, Dict, Any
import threading
from datetime import datetime
import os
from dotenv import load_dotenv

from .models import (
    AddKnowledgeRequest, AddKnowledgeResponse,
    UpdateKnowledgeMetadataRequest, UpdateKnowledgeMetadataResponse,
    DeleteKnowledgeRequest, DeleteKnowledgeResponse,
    KnowledgeCreateMessage, KnowledgeUpdateMessage, KnowledgeDeleteMessage
)

load_dotenv()

logger = logging.getLogger(__name__)


class MQHandler:
    def __init__(self, rabbitmq_url: str = None):
        self.rabbitmq_url = rabbitmq_url or os.getenv("RABBITMQ_URL", "amqp://localhost:5672")
        self.connection = None
        self.channel = None
        self.handlers: Dict[str, Callable] = {}
        self.topic_handlers: Dict[str, Callable] = {}  # For topic-based message handling
        self.is_running = False
        
        # Queue names
        self.KNOWLEDGE_QUEUE = "knowledge_operations"
        self.RESPONSE_QUEUE = "knowledge_responses"
        
        # New topic-based queues
        self.KNOWLEDGE_CREATE_QUEUE = "KNOWLEDGE_CREATE"
        self.KNOWLEDGE_UPDATE_QUEUE = "KNOWLEDGE_UPDATE"
        self.KNOWLEDGE_DELETE_QUEUE = "KNOWLEDGE_DELETE"
        
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            self.channel = self.connection.channel()
            
            # Declare existing queues
            self.channel.queue_declare(queue=self.KNOWLEDGE_QUEUE, durable=True)
            self.channel.queue_declare(queue=self.RESPONSE_QUEUE, durable=True)
            
            # Declare new topic-based queues with arguments to match existing configuration
            queue_args = {'x-message-ttl': 30000}  # Match existing TTL configuration
            
            self.channel.queue_declare(
                queue=self.KNOWLEDGE_CREATE_QUEUE, 
                durable=True, 
                arguments=queue_args
            )
            self.channel.queue_declare(
                queue=self.KNOWLEDGE_UPDATE_QUEUE, 
                durable=True, 
                arguments=queue_args
            )
            self.channel.queue_declare(
                queue=self.KNOWLEDGE_DELETE_QUEUE, 
                durable=True, 
                arguments=queue_args
            )
            
            logger.info("Connected to RabbitMQ successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    def disconnect(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

    def publish_message(self, queue: str, message: Dict[str, Any], correlation_id: str = None):
        """Publish a message to a queue"""
        try:
            if not self.channel:
                self.connect()
            
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                correlation_id=correlation_id,
                timestamp=int(datetime.now().timestamp())
            )
            
            self.channel.basic_publish(
                exchange='',
                routing_key=queue,
                body=json.dumps(message),
                properties=properties
            )
            
            logger.info(f"Published message to queue {queue}")
            
        except Exception as e:
            logger.error(f"Error publishing message to queue {queue}: {e}")
            raise

    def register_handler(self, operation: str, handler: Callable):
        """Register a handler for a specific operation"""
        self.handlers[operation] = handler
        logger.info(f"Registered handler for operation: {operation}")
        
    def register_topic_handler(self, topic: str, handler: Callable):
        """Register a handler for a specific topic"""
        self.topic_handlers[topic] = handler
        logger.info(f"Registered topic handler for: {topic}")

    def process_message(self, ch, method, properties, body):
        """Process incoming messages (legacy format)"""
        try:
            message = json.loads(body.decode('utf-8'))
            operation = message.get('operation')
            
            if operation not in self.handlers:
                logger.error(f"No handler registered for operation: {operation}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            # Process the message
            handler = self.handlers[operation]
            response = handler(message.get('data', {}))
            
            # Send response if correlation_id is provided
            if properties.correlation_id:
                response_message = {
                    'operation': operation,
                    'correlation_id': properties.correlation_id,
                    'response': response,
                    'timestamp': datetime.now().isoformat()
                }
                
                self.publish_message(
                    self.RESPONSE_QUEUE,
                    response_message,
                    correlation_id=properties.correlation_id
                )
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Successfully processed message for operation: {operation}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
    def process_topic_message(self, ch, method, properties, body):
        """Process incoming topic-based messages (new format)"""
        try:
            message_data = json.loads(body.decode('utf-8'))
            topic = method.routing_key  # The queue name is the topic
            
            logger.info(f"Processing topic message for: {topic}")
            
            if topic not in self.topic_handlers:
                logger.error(f"No handler registered for topic: {topic}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return
            
            # Process the message
            handler = self.topic_handlers[topic]
            response = handler(message_data)
            
            # Log the response
            logger.info(f"Topic message processed for {topic}: {response}")
            
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"Successfully processed topic message for: {topic}")
            
        except Exception as e:
            logger.error(f"Error processing topic message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        """Start consuming messages from all queues"""
        try:
            if not self.channel:
                self.connect()
            
            self.channel.basic_qos(prefetch_count=1)
            
            # Set up consumers for legacy queues
            self.channel.basic_consume(
                queue=self.KNOWLEDGE_QUEUE,
                on_message_callback=self.process_message
            )
            
            # Set up consumers for new topic-based queues
            self.channel.basic_consume(
                queue=self.KNOWLEDGE_CREATE_QUEUE,
                on_message_callback=self.process_topic_message
            )
            
            self.channel.basic_consume(
                queue=self.KNOWLEDGE_UPDATE_QUEUE,
                on_message_callback=self.process_topic_message
            )
            
            self.channel.basic_consume(
                queue=self.KNOWLEDGE_DELETE_QUEUE,
                on_message_callback=self.process_topic_message
            )
            
            self.is_running = True
            logger.info("Started consuming messages from all queues")
            self.channel.start_consuming()
            
        except Exception as e:
            logger.error(f"Error starting message consumption: {e}")
            raise

    def stop_consuming(self):
        """Stop consuming messages"""
        try:
            if self.channel:
                self.channel.stop_consuming()
            self.is_running = False
            logger.info("Stopped consuming messages")
        except Exception as e:
            logger.error(f"Error stopping message consumption: {e}")

    def send_knowledge_operation(self, operation: str, data: Dict[str, Any], correlation_id: str = None):
        """Send a knowledge operation message (legacy format)"""
        message = {
            'operation': operation,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.publish_message(self.KNOWLEDGE_QUEUE, message, correlation_id)
        
    def send_topic_message(self, topic: str, message_data: Dict[str, Any]):
        """Send a topic-based message (new format)"""
        queue_map = {
            "KNOWLEDGE_CREATE": self.KNOWLEDGE_CREATE_QUEUE,
            "KNOWLEDGE_UPDATE": self.KNOWLEDGE_UPDATE_QUEUE,
            "KNOWLEDGE_DELETE": self.KNOWLEDGE_DELETE_QUEUE
        }
        
        if topic not in queue_map:
            raise ValueError(f"Unknown topic: {topic}")
            
        queue = queue_map[topic]
        self.publish_message(queue, message_data)


class MQClient:
    """Client for sending messages to the MQ system"""
    
    def __init__(self, rabbitmq_url: str = None):
        self.mq_handler = MQHandler(rabbitmq_url)
        
    def add_knowledge(self, request: AddKnowledgeRequest, correlation_id: str = None):
        """Send add knowledge request (legacy)"""
        data = request.dict()
        self.mq_handler.send_knowledge_operation("add_knowledge", data, correlation_id)
        
    def update_knowledge_metadata(self, request: UpdateKnowledgeMetadataRequest, correlation_id: str = None):
        """Send update knowledge metadata request (legacy)"""
        data = request.dict()
        self.mq_handler.send_knowledge_operation("update_knowledge_metadata", data, correlation_id)
        
    def delete_knowledge(self, request: DeleteKnowledgeRequest, correlation_id: str = None):
        """Send delete knowledge request (legacy)"""
        data = request.dict()
        self.mq_handler.send_knowledge_operation("delete_knowledge", data, correlation_id)
        
    def create_knowledge(self, message: KnowledgeCreateMessage):
        """Send create knowledge message (new format)"""
        self.mq_handler.send_topic_message("KNOWLEDGE_CREATE", message.dict())
        
    def update_knowledge(self, message: KnowledgeUpdateMessage):
        """Send update knowledge message (new format)"""
        self.mq_handler.send_topic_message("KNOWLEDGE_UPDATE", message.dict())
        
    def delete_knowledge_by_id(self, message: KnowledgeDeleteMessage):
        """Send delete knowledge message (new format)"""
        self.mq_handler.send_topic_message("KNOWLEDGE_DELETE", message.dict())


def start_mq_consumer_thread(mq_handler: MQHandler):
    """Start MQ consumer in a separate thread"""
    def consumer_thread():
        try:
            mq_handler.start_consuming()
        except KeyboardInterrupt:
            logger.info("MQ consumer interrupted")
            mq_handler.stop_consuming()
        except Exception as e:
            logger.error(f"MQ consumer error: {e}")
    
    thread = threading.Thread(target=consumer_thread, daemon=True)
    thread.start()
    return thread