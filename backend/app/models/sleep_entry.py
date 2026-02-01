import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Date, DateTime, Float, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SleepEntry(Base):
    __tablename__ = "sleep_entries"

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
    bedtime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    wake_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-100
    deep_sleep_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rem_sleep_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    awakenings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="sleep_entries")

    def __repr__(self) -> str:
        return f"<SleepEntry(id={self.id}, date={self.date}, duration={self.duration_hours}h)>"
