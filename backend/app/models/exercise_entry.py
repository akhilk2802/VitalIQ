import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Date, DateTime, Float, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.utils.enums import ExerciseType, ExerciseIntensity


class ExerciseEntry(Base):
    __tablename__ = "exercise_entries"

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
    exercise_type: Mapped[ExerciseType] = mapped_column(
        SQLEnum(ExerciseType), 
        nullable=False
    )
    exercise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    intensity: Mapped[ExerciseIntensity] = mapped_column(
        SQLEnum(ExerciseIntensity), 
        nullable=False
    )
    calories_burned: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heart_rate_avg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    heart_rate_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
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
    user = relationship("User", back_populates="exercise_entries")

    def __repr__(self) -> str:
        return f"<ExerciseEntry(id={self.id}, name={self.exercise_name}, duration={self.duration_minutes}min)>"
