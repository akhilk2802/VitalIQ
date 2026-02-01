"""Schemas for prediction-related API responses"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date, datetime


class RecoveryFactors(BaseModel):
    """Factors contributing to recovery score"""
    sleep_quality: float = Field(..., description="Sleep quality contribution (0-10)")
    sleep_duration: float = Field(..., description="Sleep duration contribution (0-10)")
    deep_sleep: float = Field(..., description="Deep sleep contribution (0-10)")
    hrv: float = Field(..., description="HRV contribution (0-10)")
    resting_hr: float = Field(..., description="Resting HR contribution (0-10)")
    exercise_load: float = Field(..., description="Exercise load contribution (0-10)")


class RecoveryResponse(BaseModel):
    """Recovery readiness prediction response"""
    recovery_score: int = Field(..., ge=1, le=10, description="Recovery score 1-10")
    status: str = Field(..., description="Status: ready_for_intense, ready_for_moderate, needs_rest, recovery_day")
    message: str = Field(..., description="Human-readable recovery message")
    factors: Dict[str, float] = Field(..., description="Factor contributions")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence")


class CravingTriggers(BaseModel):
    """Factors triggering cravings"""
    low_sleep: Optional[float] = None
    low_hrv: Optional[float] = None
    stress: Optional[float] = None
    low_activity: Optional[float] = None
    high_activity: Optional[float] = None
    carb_cycle: Optional[float] = None
    dehydration: Optional[float] = None


class CravingPredictionResponse(BaseModel):
    """Single craving prediction"""
    craving_type: str = Field(..., description="Type: sugar, carbs, salty, comfort_food, none")
    likelihood: float = Field(..., ge=0, le=1, description="Probability 0-1")
    intensity: str = Field(..., description="Intensity: low, moderate, high")
    reasoning: str = Field(..., description="Human-readable explanation")
    countermeasures: List[str] = Field(..., description="Actionable countermeasures")
    peak_time: Optional[str] = Field(None, description="When craving likely peaks")
    trigger_factors: Dict[str, float] = Field(..., description="Contributing factors")


class CravingsForecastResponse(BaseModel):
    """Full day's craving forecast"""
    date: date
    primary_craving: CravingPredictionResponse
    secondary_cravings: List[CravingPredictionResponse] = Field(default_factory=list)
    overall_risk: str = Field(..., description="Overall risk: low, moderate, high")
    summary: str = Field(..., description="Summary message")
