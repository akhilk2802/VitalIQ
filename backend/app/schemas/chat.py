"""Pydantic schemas for chat API."""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID


class ChatSessionCreate(BaseModel):
    """Schema for creating a chat session."""
    title: Optional[str] = Field(None, max_length=255, description="Optional session title")


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    title: Optional[str] = Field(None, max_length=255, description="New session title")


class ChatSessionResponse(BaseModel):
    """Schema for chat session response."""
    id: UUID
    user_id: UUID
    title: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """Schema for creating/sending a chat message."""
    content: str = Field(..., min_length=1, max_length=4000, description="Message content")


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    id: UUID
    session_id: UUID
    role: str
    content: str
    context_used: Optional[Dict[str, Any]] = None
    tokens_used: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatSessionWithMessages(ChatSessionResponse):
    """Schema for session with messages."""
    messages: List[ChatMessageResponse] = []


class PaginatedMessagesResponse(BaseModel):
    """Schema for paginated messages response."""
    messages: List[ChatMessageResponse]
    has_more: bool = False
    next_cursor: Optional[UUID] = None  # ID of oldest message for next page


class ChatStreamChunk(BaseModel):
    """Schema for streaming chat response chunks."""
    type: str = Field(..., description="Chunk type: 'chunk', 'done', 'error'")
    content: Optional[str] = Field(None, description="Content for 'chunk' type")
    message_id: Optional[UUID] = Field(None, description="Message ID for 'done' type")
    error: Optional[str] = Field(None, description="Error message for 'error' type")


class QuickInsightRequest(BaseModel):
    """Schema for quick insight request."""
    insight_type: str = Field(
        "summary", 
        description="Type of insight: summary, tips, anomalies"
    )


class QuickInsightResponse(BaseModel):
    """Schema for quick insight response."""
    insight: str
    insight_type: str
    generated_at: datetime
