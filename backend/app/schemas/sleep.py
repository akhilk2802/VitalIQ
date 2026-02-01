from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date, datetime
import uuid


class SleepEntryCreate(BaseModel):
    date: date
    bedtime: datetime
    wake_time: datetime
    quality_score: int = Field(..., ge=1, le=100)
    deep_sleep_minutes: Optional[int] = Field(default=None, ge=0)
    rem_sleep_minutes: Optional[int] = Field(default=None, ge=0)
    awakenings: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @field_validator('wake_time')
    @classmethod
    def wake_time_after_bedtime(cls, v, info):
        if 'bedtime' in info.data and v <= info.data['bedtime']:
            raise ValueError('wake_time must be after bedtime')
        return v


class SleepEntryUpdate(BaseModel):
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    quality_score: Optional[int] = Field(default=None, ge=1, le=100)
    deep_sleep_minutes: Optional[int] = Field(default=None, ge=0)
    rem_sleep_minutes: Optional[int] = Field(default=None, ge=0)
    awakenings: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class SleepEntryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    bedtime: datetime
    wake_time: datetime
    duration_hours: float
    quality_score: int
    deep_sleep_minutes: Optional[int]
    rem_sleep_minutes: Optional[int]
    awakenings: Optional[int]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SleepStats(BaseModel):
    avg_duration_hours: float
    avg_quality_score: float
    avg_deep_sleep_minutes: Optional[float]
    avg_rem_sleep_minutes: Optional[float]
    total_entries: int
    best_sleep_date: Optional[date]
    worst_sleep_date: Optional[date]
