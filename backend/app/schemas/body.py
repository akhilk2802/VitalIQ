from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
import uuid


class BodyMetricsCreate(BaseModel):
    date: date
    weight_kg: float = Field(..., ge=20, le=500)
    body_fat_pct: Optional[float] = Field(default=None, ge=1, le=70)
    muscle_mass_kg: Optional[float] = Field(default=None, ge=10, le=200)
    bmi: Optional[float] = Field(default=None, ge=10, le=60)
    waist_cm: Optional[float] = Field(default=None, ge=40, le=200)
    notes: Optional[str] = None


class BodyMetricsUpdate(BaseModel):
    weight_kg: Optional[float] = Field(default=None, ge=20, le=500)
    body_fat_pct: Optional[float] = Field(default=None, ge=1, le=70)
    muscle_mass_kg: Optional[float] = Field(default=None, ge=10, le=200)
    bmi: Optional[float] = Field(default=None, ge=10, le=60)
    waist_cm: Optional[float] = Field(default=None, ge=40, le=200)
    notes: Optional[str] = None


class BodyMetricsResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    weight_kg: float
    body_fat_pct: Optional[float]
    muscle_mass_kg: Optional[float]
    bmi: Optional[float]
    waist_cm: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
