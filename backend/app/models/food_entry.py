import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Date, DateTime, Float, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.utils.enums import MealType


class FoodEntry(Base):
    __tablename__ = "food_entries"

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
    meal_type: Mapped[MealType] = mapped_column(
        SQLEnum(MealType), 
        nullable=False
    )
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fats_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sugar_g: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    fiber_g: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sodium_mg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="food_entries")

    def __repr__(self) -> str:
        return f"<FoodEntry(id={self.id}, food_name={self.food_name}, calories={self.calories})>"
