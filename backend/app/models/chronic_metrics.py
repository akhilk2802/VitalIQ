import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Date, DateTime, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.utils.enums import ChronicTimeOfDay, ConditionType


class ChronicMetrics(Base):
    __tablename__ = "chronic_metrics"

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
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    time_of_day: Mapped[ChronicTimeOfDay] = mapped_column(
        SQLEnum(ChronicTimeOfDay), 
        nullable=False
    )
    condition_type: Mapped[ConditionType] = mapped_column(
        SQLEnum(ConditionType), 
        nullable=False
    )
    
    # Diabetes fields
    blood_glucose_mgdl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    insulin_units: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hba1c_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Heart/Cholesterol fields
    cholesterol_total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cholesterol_ldl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cholesterol_hdl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    triglycerides: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # General
    medication_taken: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    symptoms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    # Source tracking for external integrations
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="manual")
    external_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="chronic_metrics")

    def __repr__(self) -> str:
        return f"<ChronicMetrics(id={self.id}, date={self.date}, condition={self.condition_type})>"
