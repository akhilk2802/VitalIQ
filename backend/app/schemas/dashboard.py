from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

from app.schemas.food import DailyNutritionSummary
from app.schemas.sleep import SleepEntryResponse
from app.schemas.exercise import ExerciseEntryResponse
from app.schemas.vitals import VitalSignsResponse
from app.schemas.body import BodyMetricsResponse
from app.schemas.chronic import ChronicMetricsResponse
from app.schemas.anomaly import AnomalyResponse


class CorrelationSummaryItem(BaseModel):
    """Lightweight correlation for dashboard display."""
    metric_a: str
    metric_b: str
    correlation_type: str
    correlation_value: float
    strength: str
    lag_days: int
    causal_direction: Optional[str]
    insight: Optional[str]
    is_actionable: bool


class DailySummary(BaseModel):
    date: date
    nutrition: Optional[DailyNutritionSummary]
    sleep: Optional[SleepEntryResponse]
    exercises: List[ExerciseEntryResponse]
    vitals: List[VitalSignsResponse]
    body_metrics: Optional[BodyMetricsResponse]
    chronic_metrics: List[ChronicMetricsResponse]
    anomalies: List[AnomalyResponse]


class DashboardResponse(BaseModel):
    user_id: str
    period_start: date
    period_end: date
    daily_summaries: List[DailySummary]
    total_anomalies: int
    unacknowledged_anomalies: int
    # Correlation data
    top_correlations: List[CorrelationSummaryItem] = []
    correlation_insights: List[str] = []


class ScoreFactorDetail(BaseModel):
    """Detailed factor breakdown for a score component"""
    score: int
    factors: List[str]
    key_metric: Optional[str] = None
    key_value: Optional[float] = None


class HealthScoreBreakdown(BaseModel):
    """Detailed breakdown of health score by category"""
    sleep: ScoreFactorDetail
    nutrition: ScoreFactorDetail
    activity: ScoreFactorDetail
    vitals: ScoreFactorDetail


class HealthScore(BaseModel):
    overall_score: int  # 0-100
    sleep_score: int
    nutrition_score: int
    activity_score: int
    vitals_score: int
    trend: str  # "improving", "stable", "declining"
    computed_at: datetime


class HealthScoreDetailed(BaseModel):
    """Enhanced health score with detailed breakdown"""
    overall_score: int
    breakdown: HealthScoreBreakdown
    trend: str
    comparison_to_last_week: Optional[int] = None  # Score difference
    top_improvement_area: Optional[str] = None
    top_strength_area: Optional[str] = None
    insights: List[str] = []
    computed_at: datetime
