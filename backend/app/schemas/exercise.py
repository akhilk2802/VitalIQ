from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import uuid

from app.utils.enums import ExerciseType, ExerciseIntensity


class ExerciseEntryCreate(BaseModel):
    date: date
    exercise_type: ExerciseType
    exercise_name: str = Field(..., min_length=1, max_length=255)
    duration_minutes: int = Field(..., ge=1)
    intensity: ExerciseIntensity
    calories_burned: Optional[int] = Field(default=None, ge=0)
    heart_rate_avg: Optional[int] = Field(default=None, ge=30, le=250)
    heart_rate_max: Optional[int] = Field(default=None, ge=30, le=250)
    distance_km: Optional[float] = Field(default=None, ge=0)
    sets: Optional[int] = Field(default=None, ge=1)
    reps: Optional[int] = Field(default=None, ge=1)
    weight_kg: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class ExerciseEntryUpdate(BaseModel):
    exercise_type: Optional[ExerciseType] = None
    exercise_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    duration_minutes: Optional[int] = Field(default=None, ge=1)
    intensity: Optional[ExerciseIntensity] = None
    calories_burned: Optional[int] = Field(default=None, ge=0)
    heart_rate_avg: Optional[int] = Field(default=None, ge=30, le=250)
    heart_rate_max: Optional[int] = Field(default=None, ge=30, le=250)
    distance_km: Optional[float] = Field(default=None, ge=0)
    sets: Optional[int] = Field(default=None, ge=1)
    reps: Optional[int] = Field(default=None, ge=1)
    weight_kg: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class ExerciseEntryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    exercise_type: ExerciseType
    exercise_name: str
    duration_minutes: int
    intensity: ExerciseIntensity
    calories_burned: Optional[int]
    heart_rate_avg: Optional[int]
    heart_rate_max: Optional[int]
    distance_km: Optional[float]
    sets: Optional[int]
    reps: Optional[int]
    weight_kg: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WeeklyExerciseSummary(BaseModel):
    week_start: date
    week_end: date
    total_duration_minutes: int
    total_calories_burned: int
    workout_count: int
    workouts_by_type: dict[str, int]
    avg_intensity: str
    entries: List[ExerciseEntryResponse]
