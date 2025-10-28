# RAG Backend Microservice

A Python-based RAG (Retrieval Augmented Generation) **microservice** that:

1. **Consumes MQ messages** from your external backend for knowledge operations
2. **Provides HTTP endpoints** for chat functionality with streaming responses
3. **Supports flexible deployment** modes (HTTP+MQ or MQ-only)

## 🏗️ Microservice Architecture

```
External Backend → MQ Messages → RAG Microservice → ChromaDB
                                      ↓
                              HTTP Chat Endpoints ← Clients
```

### **Message Flow:**
- **Knowledge Operations**: External Backend → RabbitMQ → This Microservice → ChromaDB
- **Chat Operations**: Clients → HTTP API → This Microservice → OpenAI + ChromaDB

## 🚀 Deployment Modes

### **1. Full Service (HTTP + MQ) - Default**
```bash
python main.py
```
- Starts HTTP API for chat endpoints
- Starts MQ consumer for knowledge operations
- Best for: Complete RAG functionality

### **2. MQ-Only Service**
```bash
python main.py --mq-only
# OR
python -m src.mq_service
```
- Only MQ consumer (no HTTP API)
- Best for: Dedicated knowledge processing worker

## 📋 Features

### **Knowledge Management (MQ-based)**
- **Automatic Text Chunking**: Intelligent document splitting with overlap
- **Vector Embeddings**: OpenAI-based embeddings stored in ChromaDB
- **Metadata Filtering**: Tenant and role-based access control
- **Batch Operations**: Efficient bulk document processing

### **Chat with RAG (HTTP-based)**
- **Real-time Streaming**: Server-sent events for live responses
- **Source Attribution**: Shows which documents informed the answer
- **Context-aware**: Maintains conversation history
- **Access Control**: Respects user tenant/role permissions

### **Multi-tenant Support**
- **Tenant Isolation**: Documents filtered by tenant_id
- **Role-based Access**: Additional filtering by user roles
- **Secure**: No cross-tenant data leakage

## 🛠️ Setup

### **Prerequisites**
- Python 3.8+
- RabbitMQ server
- OpenAI API key

### **Installation**
```bash
# Clone and install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

### **Start RabbitMQ**
```bash
# Using Docker
docker run -d --name rabbitmq -p 5672:5672 rabbitmq:3

# Or install locally (macOS)
brew install rabbitmq
brew services start rabbitmq
```

## 🔌 API Endpoints

### **Chat Service (HTTP)**
```bash
# Complete response with sources
POST /chat/send
{
  "message": "What is machine learning?",
  "user_attributes": {
    "tenant_id": "company_a",
    "role": "user"
  },
  "conversation_history": []
}

# Streaming response
POST /chat/stream
# Same request format, returns Server-Sent Events
```

### **System Endpoints**
```bash
GET /health          # Service health check
GET /stats           # ChromaDB statistics
```

## 📨 MQ Message Contracts

Your external backend should send these message types:

### **AddKnowledge**
```json
{
  "operation": "add_knowledge",
  "data": {
    "content": "Document text content...",
    "metadata": {
      "title": "Document Title",
      "source": "document.pdf",
      "tenant_id": "company_a",
      "tags": ["ml", "ai"],
      "custom_field": "value"
    },
    "user_attributes": {
      "tenant_id": "company_a",
      "role": "admin"
    }
  }
}
```

### **UpdateKnowledgeMetadata**
```json
{
  "operation": "update_knowledge_metadata",
  "data": {
    "knowledge_id": "doc_123",
    "metadata": {
      "title": "Updated Title",
      "tags": ["updated", "tags"]
    },
    "user_attributes": {
      "tenant_id": "company_a",
      "role": "admin"
    }
  }
}
```

### **DeleteKnowledge**
```json
{
  "operation": "delete_knowledge",
  "data": {
    "knowledge_id": "doc_123",
    "user_attributes": {
      "tenant_id": "company_a",
      "role": "admin"
    }
  }
}
```

## 🔧 Configuration

### **Environment Variables**
```bash
# Required
OPENAI_API_KEY=your_openai_api_key

# Optional
RABBITMQ_URL=amqp://localhost:5672
CHROMA_PERSIST_DIRECTORY=./chroma_db
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## 🏃‍♂️ Running the Service

### **Development**
```bash
# Full service (recommended for development)
python main.py

# MQ-only (for testing message consumption)
python main.py --mq-only
```

### **Production**
```bash
# Using gunicorn for HTTP service
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api:app

# Or systemd service for MQ-only
python main.py --mq-only
```

## 📁 Project Structure

```
├── src/
│   ├── api.py              # FastAPI HTTP endpoints
│   ├── mq_service.py       # Pure MQ consumer service
│   ├── chat_service.py     # RAG chat functionality
│   ├── knowledge_service.py # Knowledge management
│   ├── vector_store.py     # ChromaDB integration
│   ├── mq_handler.py       # RabbitMQ handling
│   └── models.py           # Data models
├── main.py                 # Entry point with deployment modes
├── requirements.txt        # Dependencies
└── .env.example           # Environment template
```

## 🔒 Access Control

The microservice implements **tenant-based isolation**:

- Documents are filtered by `tenant_id` in metadata
- Users can only access documents from their tenant
- Role-based filtering provides additional access control
- No cross-tenant data leakage

## 🚀 Integration with Your Backend

1. **Send MQ Messages**: Your backend publishes knowledge operations to RabbitMQ
2. **This Service Processes**: Automatically handles chunking, embedding, and storage
3. **Clients Chat**: Direct HTTP calls to this service for chat functionality
4. **Responses Include Sources**: Chat responses show which documents were used

This microservice architecture allows you to **decouple knowledge management** from your main backend while providing **real-time chat capabilities** to your clients!