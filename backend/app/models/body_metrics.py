import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Date, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class BodyMetrics(Base):
    __tablename__ = "body_metrics"

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
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    body_fat_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    muscle_mass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bmi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="body_metrics")

    def __repr__(self) -> str:
        return f"<BodyMetrics(id={self.id}, date={self.date}, weight={self.weight_kg}kg)>"
