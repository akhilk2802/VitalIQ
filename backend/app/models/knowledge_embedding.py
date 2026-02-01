"""Knowledge embedding model for RAG system."""

import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from pgvector.sqlalchemy import Vector

from app.database import Base
from app.utils.enums import KnowledgeSourceType

# Embedding dimensions for text-embedding-3-large
EMBEDDING_DIMENSIONS = 3072


class KnowledgeEmbedding(Base):
    """
    Stores embeddings for health knowledge base content.
    
    Sources include:
    - Curated markdown files (sleep science, HRV, etc.)
    - PubMed research abstracts
    - MedlinePlus health topics
    """
    __tablename__ = "knowledge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Content and embedding
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    
    # Source information
    source_type: Mapped[KnowledgeSourceType] = mapped_column(
        ENUM(KnowledgeSourceType, name='knowledgesourcetype', create_type=False),
        nullable=False
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True
    )  # e.g., PMID for PubMed, file path for curated
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Additional metadata (tags, categories, etc.)
    extra_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    # For chunked documents
    chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
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

    def __repr__(self) -> str:
        return f"<KnowledgeEmbedding(id={self.id}, source={self.source_type.value}, title={self.title})>"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "content": self.content,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "title": self.title,
            "metadata": self.extra_metadata,
            "chunk_index": self.chunk_index,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
