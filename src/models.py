from typing import List, Optional, Literal, Union
from pydantic import BaseModel, field_validator
from datetime import datetime


class UserTenant(BaseModel):
    tenantId: str
    tenantRole: str


class UserAttributes(BaseModel):
    userId: str
    operationIds: List[str]
    userTenants: List[UserTenant]


# New message contract models for RabbitMQ
class KnowledgeMessageMetadata(BaseModel):
    knowledgeId: str
    type: Literal["CASE", "ARTICLE"]
    access: Literal["PUBLIC", "TENANT", "EMAIL"]
    tenantId: Optional[str] = None
    accessUserIds: Optional[List[str]] = None


class KnowledgeCreateMessage(BaseModel):
    metadata: KnowledgeMessageMetadata
    content: str
    fileType: Optional[str] = None
    fileUrls: List[str]
    
    @field_validator('fileType')
    @classmethod
    def validate_file_type(cls, v):
        """Make fileType case-insensitive by converting to lowercase and validating"""
        if v is None:
            return v  # Allow None values
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower not in ["pdf", "image"]:
                raise ValueError(f"fileType must be 'pdf' or 'image' (case-insensitive), got '{v}'")
            return v_lower
        return v


class KnowledgeUpdateMessage(BaseModel):
    metadata: KnowledgeMessageMetadata
    content: str
    fileType: Optional[str] = None
    fileUrls: List[str]
    
    @field_validator('fileType')
    @classmethod
    def validate_file_type(cls, v):
        """Make fileType case-insensitive by converting to lowercase and validating"""
        if v is None:
            return v  # Allow None values
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower not in ["pdf", "image"]:
                raise ValueError(f"fileType must be 'pdf' or 'image' (case-insensitive), got '{v}'")
            return v_lower
        return v


class KnowledgeDeleteMessage(BaseModel):
    knowledgeId: str


# Existing models (keeping for backward compatibility)
class KnowledgeMetadata(BaseModel):
    tenantId: Optional[str] = None
    tenantRoleIds: Optional[List[str]] = None
    type: Literal["ARTICLE", "FILE"]
    isGlobal: bool


class Knowledge(BaseModel):
    id: Optional[str] = None
    content: str
    metadata: KnowledgeMetadata
    filetype: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class KnowledgeChunk(BaseModel):
    id: str
    knowledge_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: KnowledgeMetadata
    chunk_index: int


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: Optional[datetime] = None
    knowledge_id: Optional[str] = None  # Optional knowledge ID for context retrieval


class ChatHistory(BaseModel):
    messages: List[ChatMessage]


class ChatRequest(BaseModel):
    chathistory: ChatHistory
    message: str
    user_attributes: UserAttributes


class StreamingChatRequest(BaseModel):
    chatHistory: List[ChatMessage]
    message: str
    userAttributes: UserAttributes


class Source(BaseModel):
    knowledge_id: str
    chunk_id: str
    content: str
    metadata: KnowledgeMetadata
    relevance_score: float


class ChatResponse(BaseModel):
    response: str
    sources: List[Source]


class AddKnowledgeRequest(BaseModel):
    content: str
    metadata: KnowledgeMetadata
    filetype: Optional[str] = None
    url: Optional[str] = None


class AddKnowledgeResponse(BaseModel):
    knowledge_id: str
    chunk_ids: List[str]
    status: str


class UpdateKnowledgeMetadataRequest(BaseModel):
    knowledge_id: str
    metadata: KnowledgeMetadata


class UpdateKnowledgeMetadataResponse(BaseModel):
    status: str


class DeleteKnowledgeRequest(BaseModel):
    knowledge_id: str


class DeleteKnowledgeResponse(BaseModel):
    status: str