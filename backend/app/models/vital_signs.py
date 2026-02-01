import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Date, DateTime, Float, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.utils.enums import TimeOfDay


class VitalSigns(Base):
    __tablename__ = "vital_signs"

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
    time_of_day: Mapped[TimeOfDay] = mapped_column(
        SQLEnum(TimeOfDay), 
        nullable=False
    )
    resting_heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hrv_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blood_pressure_systolic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blood_pressure_diastolic: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    body_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
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
    user = relationship("User", back_populates="vital_signs")

    def __repr__(self) -> str:
        return f"<VitalSigns(id={self.id}, date={self.date}, hr={self.resting_heart_rate})>"
