from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
import uuid

from app.utils.enums import TimeOfDay


class VitalSignsCreate(BaseModel):
    date: date
    time_of_day: TimeOfDay
    resting_heart_rate: Optional[int] = Field(default=None, ge=30, le=250)
    hrv_ms: Optional[int] = Field(default=None, ge=0, le=300)
    blood_pressure_systolic: Optional[int] = Field(default=None, ge=60, le=250)
    blood_pressure_diastolic: Optional[int] = Field(default=None, ge=40, le=150)
    respiratory_rate: Optional[int] = Field(default=None, ge=5, le=60)
    body_temperature: Optional[float] = Field(default=None, ge=35.0, le=42.0)
    spo2: Optional[int] = Field(default=None, ge=70, le=100)


class VitalSignsUpdate(BaseModel):
    time_of_day: Optional[TimeOfDay] = None
    resting_heart_rate: Optional[int] = Field(default=None, ge=30, le=250)
    hrv_ms: Optional[int] = Field(default=None, ge=0, le=300)
    blood_pressure_systolic: Optional[int] = Field(default=None, ge=60, le=250)
    blood_pressure_diastolic: Optional[int] = Field(default=None, ge=40, le=150)
    respiratory_rate: Optional[int] = Field(default=None, ge=5, le=60)
    body_temperature: Optional[float] = Field(default=None, ge=35.0, le=42.0)
    spo2: Optional[int] = Field(default=None, ge=70, le=100)


class VitalSignsResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    time_of_day: TimeOfDay
    resting_heart_rate: Optional[int]
    hrv_ms: Optional[int]
    blood_pressure_systolic: Optional[int]
    blood_pressure_diastolic: Optional[int]
    respiratory_rate: Optional[int]
    body_temperature: Optional[float]
    spo2: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
