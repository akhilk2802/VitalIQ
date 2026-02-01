from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import uuid

from app.utils.enums import ChronicTimeOfDay, ConditionType


class ChronicMetricsCreate(BaseModel):
    date: date
    time_of_day: ChronicTimeOfDay
    condition_type: ConditionType
    
    # Diabetes fields
    blood_glucose_mgdl: Optional[float] = Field(default=None, ge=20, le=600)
    insulin_units: Optional[float] = Field(default=None, ge=0, le=100)
    hba1c_pct: Optional[float] = Field(default=None, ge=4, le=15)
    
    # Heart/Cholesterol fields
    cholesterol_total: Optional[float] = Field(default=None, ge=50, le=500)
    cholesterol_ldl: Optional[float] = Field(default=None, ge=20, le=300)
    cholesterol_hdl: Optional[float] = Field(default=None, ge=10, le=150)
    triglycerides: Optional[float] = Field(default=None, ge=30, le=1000)
    
    # General
    medication_taken: Optional[str] = Field(default=None, max_length=500)
    symptoms: Optional[str] = None
    notes: Optional[str] = None


class ChronicMetricsUpdate(BaseModel):
    time_of_day: Optional[ChronicTimeOfDay] = None
    condition_type: Optional[ConditionType] = None
    blood_glucose_mgdl: Optional[float] = Field(default=None, ge=20, le=600)
    insulin_units: Optional[float] = Field(default=None, ge=0, le=100)
    hba1c_pct: Optional[float] = Field(default=None, ge=4, le=15)
    cholesterol_total: Optional[float] = Field(default=None, ge=50, le=500)
    cholesterol_ldl: Optional[float] = Field(default=None, ge=20, le=300)
    cholesterol_hdl: Optional[float] = Field(default=None, ge=10, le=150)
    triglycerides: Optional[float] = Field(default=None, ge=30, le=1000)
    medication_taken: Optional[str] = Field(default=None, max_length=500)
    symptoms: Optional[str] = None
    notes: Optional[str] = None


class ChronicMetricsResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    time_of_day: ChronicTimeOfDay
    condition_type: ConditionType
    blood_glucose_mgdl: Optional[float]
    insulin_units: Optional[float]
    hba1c_pct: Optional[float]
    cholesterol_total: Optional[float]
    cholesterol_ldl: Optional[float]
    cholesterol_hdl: Optional[float]
    triglycerides: Optional[float]
    medication_taken: Optional[str]
    symptoms: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ChronicTrendData(BaseModel):
    date: date
    value: float
    time_of_day: ChronicTimeOfDay


class ChronicTrends(BaseModel):
    condition_type: ConditionType
    metric_name: str
    data: List[ChronicTrendData]
    avg_value: float
    min_value: float
    max_value: float
