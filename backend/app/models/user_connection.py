import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.utils.enums import DataSource, ConnectionStatus


class UserConnection(Base):
    """Track connected external data sources per user"""
    __tablename__ = "user_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    provider: Mapped[DataSource] = mapped_column(
        SQLEnum(DataSource), 
        nullable=False
    )
    vital_user_id: Mapped[Optional[str]] = mapped_column(
        String(255), 
        nullable=True
    )
    status: Mapped[ConnectionStatus] = mapped_column(
        SQLEnum(ConnectionStatus), 
        nullable=False,
        default=ConnectionStatus.pending
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True
    )
    sync_cursor: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True
    )
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
    user = relationship("User", back_populates="connections")
    raw_sync_data = relationship("RawSyncData", back_populates="connection", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<UserConnection(id={self.id}, provider={self.provider}, status={self.status})>"
