# MQ Message Format Documentation

This document describes the message queue (MQ) format used by the Radikari AI RAG Backend Microservice for knowledge management operations.

## Overview

The RAG service consumes messages from RabbitMQ to perform knowledge operations (CREATE, UPDATE, DELETE). All messages follow a standardized format with metadata and operation-specific content.

## Message Types

### 1. CREATE KNOWLEDGE

Creates new knowledge entries in the vector database.

#### Message Structure

```json
{
  "metadata": {
    "knowledgeId": "string",
    "type": "ARTICLE | FILE",
    "access": "PUBLIC | TENANT | EMAIL",
    "tenantId": "string",
    "accessUserIds": ["string"]
  },
  "content": "string",
  "fileType": "string",
  "fileUrls": ["string"]
}
```

#### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metadata.knowledgeId` | string | Yes | Unique identifier for the knowledge entry |
| `metadata.type` | string | Yes | Type of knowledge: `ARTICLE` or `FILE` |
| `metadata.access` | string | Yes | Access level: `PUBLIC`, `TENANT`, or `EMAIL` |
| `metadata.tenantId` | string | Yes | Tenant identifier for multi-tenancy |
| `metadata.accessUserIds` | array | No | List of user IDs with access (for EMAIL access type) |
| `content` | string | Yes | Main text content of the knowledge |
| `fileType` | string | Yes | File type (e.g., "pdf", "txt", "docx") |
| `fileUrls` | array | No | URLs to associated files for processing |

#### Example

```json
{
  "metadata": {
    "knowledgeId": "kb_001",
    "type": "ARTICLE",
    "access": "TENANT",
    "tenantId": "tenant_123",
    "accessUserIds": []
  },
  "content": "This is the main content of the knowledge article...",
  "fileType": "txt",
  "fileUrls": []
}
```

### 2. UPDATE KNOWLEDGE

Updates existing knowledge metadata (does not update content).

#### Message Structure

```json
{
  "metadata": {
    "knowledgeId": "string",
    "type": "ARTICLE | FILE",
    "access": "PUBLIC | TENANT | EMAIL",
    "tenantId": "string",
    "accessUserIds": ["string"]
  }
}
```

#### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metadata.knowledgeId` | string | Yes | Unique identifier for the knowledge entry to update |
| `metadata.type` | string | Yes | Updated type of knowledge |
| `metadata.access` | string | Yes | Updated access level |
| `metadata.tenantId` | string | Yes | Updated tenant identifier |
| `metadata.accessUserIds` | array | No | Updated list of user IDs with access |

#### Example

```json
{
  "metadata": {
    "knowledgeId": "kb_001",
    "type": "ARTICLE",
    "access": "PUBLIC",
    "tenantId": "tenant_123",
    "accessUserIds": []
  }
}
```

### 3. DELETE KNOWLEDGE

Removes knowledge entries from the vector database.

#### Message Structure

```json
{
  "knowledgeId": "string"
}
```

#### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `knowledgeId` | string | Yes | Unique identifier for the knowledge entry to delete |

#### Example

```json
{
  "knowledgeId": "kb_001"
}
```

## Access Types

### PUBLIC
- Knowledge is accessible to all users across all tenants
- No user-specific restrictions apply

### TENANT
- Knowledge is accessible only to users within the specified tenant
- Tenant-level access control

### EMAIL
- Knowledge is accessible only to specific users listed in `accessUserIds`
- User-level access control
- Requires `accessUserIds` array to be populated

## File Processing

### Supported File Types
- `pdf`: PDF documents (automatically processed and text extracted)
- `txt`: Plain text files
- `docx`: Word documents
- `md`: Markdown files

### PDF Processing
When `fileType` is "pdf" and `fileUrls` are provided:
1. The service downloads and processes PDF files
2. Text is extracted using OCR/text extraction
3. Extracted text is appended to the main `content`
4. If PDF processing fails, the operation continues with original content

## Queue Configuration

### Queue Names
- **Legacy Format**: `knowledge_queue`
- **Topic-based Format**: Uses routing keys for different operations

### Routing Keys (Topic-based)
- `knowledge.create`: For CREATE operations
- `knowledge.update`: For UPDATE operations  
- `knowledge.delete`: For DELETE operations

## Error Handling

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "knowledgeId": "kb_001"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "knowledgeId": "kb_001"
}
```

## Integration with Chat API

### Knowledge ID in Chat Messages

The chat API now supports referencing specific knowledge through the `knowledge_id` field in chat messages:

```json
{
  "role": "user",
  "content": "Tell me about this document",
  "knowledge_id": "kb_001",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

When processing chat requests, the service will:
1. Extract `knowledge_id` values from chat history
2. Retrieve relevant chunks using both semantic search and knowledge IDs
3. Combine and deduplicate results for comprehensive context

## Best Practices

1. **Unique Knowledge IDs**: Always use unique, descriptive knowledge IDs
2. **Appropriate Access Levels**: Choose the most restrictive access level that meets your needs
3. **Content Quality**: Ensure content is well-formatted and meaningful
4. **File URL Validation**: Verify file URLs are accessible before sending messages
5. **Error Handling**: Implement proper error handling for failed operations
6. **Batch Operations**: Consider batching multiple operations when possible

## Monitoring and Logging

The service logs all MQ operations with the following information:
- Operation type (CREATE/UPDATE/DELETE)
- Knowledge ID
- Success/failure status
- Processing time
- Error details (if applicable)

Monitor these logs for operational insights and troubleshooting.