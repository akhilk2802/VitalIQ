"""User history embedding model for personalized RAG."""

import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.utils.enums import HistoryEntityType

# Embedding dimensions for text-embedding-3-large
EMBEDDING_DIMENSIONS = 3072


class UserHistoryEmbedding(Base):
    """
    Stores embeddings for user-specific health history.
    
    Indexed entities include:
    - Anomalies (with explanations)
    - Correlations (with insights)
    - AI-generated insights
    - Chat messages (for conversation memory)
    """
    __tablename__ = "user_history_embeddings"

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
    
    # Content and embedding
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    
    # Entity reference
    entity_type: Mapped[HistoryEntityType] = mapped_column(
        ENUM(HistoryEntityType, name='historyentitytype', create_type=False),
        nullable=False
    )
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        nullable=True
    )  # Reference to the original entity (anomaly, correlation, etc.)
    
    # Additional metadata (metric names, dates, severity, etc.)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="history_embeddings")

    def __repr__(self) -> str:
        return f"<UserHistoryEmbedding(id={self.id}, user_id={self.user_id}, type={self.entity_type.value})>"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "content": self.content,
            "entity_type": self.entity_type.value,
            "entity_id": str(self.entity_id) if self.entity_id else None,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
