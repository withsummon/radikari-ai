# RAG Service API Documentation

## Overview

The RAG (Retrieval-Augmented Generation) service provides intelligent chat capabilities with knowledge retrieval and streaming responses. The service supports both traditional chat and real-time streaming chat with user attribute-based filtering.

**Base URL**: `http://localhost:8000`

## Authentication & Authorization

The service uses user attributes for access control:
- `operationIds`: List of operation permissions
- `userTenants`: List of tenant access with roles

## Endpoints

### 1. Health Check

**GET** `/health`

Check if the service is running and healthy.

#### Response
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

---

### 2. Service Statistics

**GET** `/stats`

Get service statistics and metrics.

#### Response
```json
{
  "total_documents": 150,
  "total_chunks": 1250,
  "service_uptime": "2h 30m",
  "last_updated": "2024-01-01T12:00:00Z"
}
```

---

### 3. Traditional Chat

**POST** `/chat/send`

Send a chat message and receive a complete response.

#### Request Body
```json
{
  "message": "What are the company vacation policies?",
  "userAttributes": {
    "userId": "user-123",
    "operationIds": ["HR_READ", "POLICY_VIEW"],
    "userTenants": [
      {
        "tenantId": "company-abc",
        "tenantRole": "employee"
      }
    ]
  }
}
```

#### Response
```json
{
  "response": "Based on the company policies, employees are entitled to...",
  "sources": [
    {
      "id": "doc-123",
      "title": "Employee Handbook",
      "content": "Vacation policy excerpt...",
      "metadata": {
        "page": 15,
        "section": "Benefits"
      }
    }
  ]
}
```

---

### 4. Streaming Chat

**POST** `/chat/stream`

Send a chat message and receive a streaming response.

#### Request Body
```json
{
  "message": "Explain the company benefits package",
  "userAttributes": {
    "userId": "user-123",
    "operationIds": ["HR_READ"],
    "userTenants": [
      {
        "tenantId": "company-abc",
        "tenantRole": "employee"
      }
    ]
  }
}
```

#### Response
Streaming JSON objects separated by newlines:
```json
{"type": "content", "content": "The company"}
{"type": "content", "content": " benefits package"}
{"type": "content", "content": " includes..."}
{"type": "sources", "sources": [...]}
{"type": "end"}
```

---

### 5. Streaming SSE Chat (New)

**POST** `/chat/stream-sse`

Send a chat message with conversation history and receive a Server-Sent Events (SSE) streaming response.

#### Request Body
```json
{
  "chatHistory": [
    {
      "role": "user",
      "content": "Hello, I need help with company policies",
      "timestamp": "2024-01-01T12:00:00Z"
    },
    {
      "role": "assistant",
      "content": "I'd be happy to help with company policies. What specific area are you interested in?",
      "timestamp": "2024-01-01T12:00:30Z"
    }
  ],
  "message": "What are the vacation policies for employees?",
  "userAttributes": {
    "userId": "user-123",
    "operationIds": ["HR_READ", "POLICY_VIEW"],
    "userTenants": [
      {
        "tenantId": "company-abc",
        "tenantRole": "employee"
      }
    ]
  }
}
```

#### Headers
```
Content-Type: application/json
Accept: text/event-stream
Cache-Control: no-cache
```

#### Response
Server-Sent Events stream:
```
event: message
data: {"type": "content", "content": "Based on"}

event: message
data: {"type": "content", "content": " your"}

event: message
data: {"type": "content", "content": " company's"}

event: sources
data: {"type": "sources", "sources": [{"id": "doc-123", "title": "HR Policy", "content": "..."}]}

event: end
data: {"type": "end"}
```

#### SSE Event Types

| Event Type | Description | Data Format |
|------------|-------------|-------------|
| `message` | Streaming content chunk | `{"type": "content", "content": "text chunk"}` |
| `sources` | Knowledge sources used | `{"type": "sources", "sources": [...]}` |
| `end` | Stream completion | `{"type": "end"}` |
| `error` | Error occurred | `{"type": "error", "message": "error description"}` |

---

## Data Models

### UserAttributes
```json
{
  "userId": "string",
  "operationIds": ["string"],
  "userTenants": [
    {
      "tenantId": "string",
      "tenantRole": "string"
    }
  ]
}
```

### ChatMessage
```json
{
  "role": "user|assistant",
  "content": "string",
  "timestamp": "ISO 8601 datetime string"
}
```

### Source
```json
{
  "id": "string",
  "title": "string",
  "content": "string",
  "metadata": {
    "page": "number",
    "section": "string",
    "document_type": "string"
  }
}
```

### StreamingChatRequest
```json
{
  "chatHistory": ["ChatMessage"],
  "message": "string",
  "userAttributes": "UserAttributes"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request format or missing required fields"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing user attributes"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions to access requested resources"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error occurred"
}
```

---

## Usage Examples

### JavaScript/TypeScript (SSE)

```javascript
const response = await fetch('/chat/stream-sse', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
    'Cache-Control': 'no-cache'
  },
  body: JSON.stringify({
    chatHistory: [],
    message: "What are the company policies?",
    userAttributes: {
      userId: "user-123",
      operationIds: ["HR_READ"],
      userTenants: [{ tenantId: "company-abc", tenantRole: "employee" }]
    }
  })
});

const eventSource = new EventSource('/chat/stream-sse');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'content') {
    console.log('Content:', data.content);
  } else if (data.type === 'sources') {
    console.log('Sources:', data.sources);
  } else if (data.type === 'end') {
    eventSource.close();
  }
};
```

### Python (requests)

```python
import requests
import json

# Traditional chat
response = requests.post('http://localhost:8000/chat/send', json={
    "message": "What are the vacation policies?",
    "userAttributes": {
        "userId": "user-123",
        "operationIds": ["HR_READ"],
        "userTenants": [{"tenantId": "company-abc", "tenantRole": "employee"}]
    }
})

# Streaming SSE chat
response = requests.post('http://localhost:8000/chat/stream-sse', 
    json={
        "chatHistory": [],
        "message": "What are the vacation policies?",
        "userAttributes": {
            "userId": "user-123",
            "operationIds": ["HR_READ"],
            "userTenants": [{"tenantId": "company-abc", "tenantRole": "employee"}]
        }
    },
    headers={'Accept': 'text/event-stream'},
    stream=True
)

for line in response.iter_lines(decode_unicode=True):
    if line.startswith('data:'):
        data = json.loads(line[5:])
        print(f"Received: {data}")
```

### cURL

```bash
# Traditional chat
curl -X POST http://localhost:8000/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the vacation policies?",
    "userAttributes": {
      "userId": "user-123",
      "operationIds": ["HR_READ"],
      "userTenants": [{"tenantId": "company-abc", "tenantRole": "employee"}]
    }
  }'

# Streaming SSE chat
curl -X POST http://localhost:8000/chat/stream-sse \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "chatHistory": [],
    "message": "What are the vacation policies?",
    "userAttributes": {
      "userId": "user-123",
      "operationIds": ["HR_READ"],
      "userTenants": [{"tenantId": "company-abc", "tenantRole": "employee"}]
    }
  }'
```

---

## Rate Limiting

- **Traditional Chat**: 60 requests per minute per user
- **Streaming Chat**: 30 requests per minute per user
- **SSE Chat**: 30 requests per minute per user

---

## WebSocket Support

Currently not supported. Use the SSE endpoint for real-time streaming.

---

## Testing

Use the provided test script to verify the streaming functionality:

```bash
python test_streaming_chat.py
```

---

## Docker Deployment

```bash
# Build the image
docker build -t rag-service .

# Run with Docker Compose
docker-compose -f docker-compose.test.yml up
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM | Required |
| `RABBITMQ_URL` | RabbitMQ connection URL | `amqp://guest:guest@localhost:5672/` |
| `CHROMA_PERSIST_DIRECTORY` | ChromaDB storage path | `./chroma_db` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
---

## Support

For issues or questions, please check the logs or contact the development team.