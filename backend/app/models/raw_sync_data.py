import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base
from app.utils.enums import DataSource, SyncStatus, SyncDataType


class RawSyncData(Base):
    """Staging table for raw external data before normalization"""
    __tablename__ = "raw_sync_data"

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
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("user_connections.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    provider: Mapped[DataSource] = mapped_column(
        SQLEnum(DataSource), 
        nullable=False
    )
    data_type: Mapped[SyncDataType] = mapped_column(
        SQLEnum(SyncDataType), 
        nullable=False
    )
    external_id: Mapped[str] = mapped_column(
        String(500), 
        nullable=False,
        index=True
    )
    raw_payload: Mapped[dict] = mapped_column(
        JSONB, 
        nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True
    )
    processing_status: Mapped[SyncStatus] = mapped_column(
        SQLEnum(SyncStatus), 
        nullable=False,
        default=SyncStatus.pending
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True
    )
    normalized_table: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True
    )
    normalized_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        nullable=True
    )

    # Relationships
    user = relationship("User", back_populates="raw_sync_data")
    connection = relationship("UserConnection", back_populates="raw_sync_data")

    def __repr__(self) -> str:
        return f"<RawSyncData(id={self.id}, provider={self.provider}, data_type={self.data_type}, status={self.processing_status})>"
