"""Chat models for conversational RAG system."""

import uuid
from datetime import datetime
from typing import Optional, Any, List
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM

from app.database import Base
from app.utils.enums import MessageRole


class ChatSession(Base):
    """
    Represents a chat conversation session between user and VitalIQ assistant.
    
    Each session contains multiple messages and tracks conversation context.
    """
    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # User ownership
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Session info
    title: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True
    )  # Auto-generated from first message or user-provided
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", 
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
    
    def to_dict(self, include_messages: bool = False) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            result["messages"] = [msg.to_dict() for msg in self.messages]
        return result


class ChatMessage(Base):
    """
    Represents a single message in a chat session.
    
    Stores both user messages and assistant responses,
    along with the RAG context used for generation.
    """
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Session reference
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Message content
    role: Mapped[MessageRole] = mapped_column(
        ENUM(MessageRole, name='messagerole', create_type=False),
        nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # RAG context used for assistant responses
    context_used: Mapped[Optional[dict]] = mapped_column(
        JSONB, 
        nullable=True
    )  # Stores retrieved chunks and sources
    
    # Token usage tracking
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", 
        back_populates="messages"
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(id={self.id}, role={self.role.value}, content={content_preview})>"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "role": self.role.value,
            "content": self.content,
            "context_used": self.context_used,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
