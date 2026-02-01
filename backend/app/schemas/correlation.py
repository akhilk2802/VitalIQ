"""Pydantic schemas for correlation API."""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import uuid

from app.utils.enums import CorrelationType, CorrelationStrength, CausalDirection


class CorrelationResponse(BaseModel):
    """Response schema for a single correlation."""
    id: uuid.UUID
    user_id: uuid.UUID
    metric_a: str
    metric_b: str
    correlation_type: CorrelationType
    correlation_value: float
    strength: CorrelationStrength
    p_value: Optional[float]
    is_significant: bool
    lag_days: int
    causal_direction: Optional[CausalDirection]
    granger_f_stat: Optional[float]
    granularity: str
    period_start: date
    period_end: date
    sample_size: int
    insight: Optional[str]
    recommendation: Optional[str]
    population_avg: Optional[float]
    percentile_rank: Optional[float]
    is_actionable: bool
    confidence_score: Optional[float]
    detected_at: datetime

    class Config:
        from_attributes = True


class CorrelationSummary(BaseModel):
    """Lightweight correlation summary for dashboard."""
    metric_a: str
    metric_b: str
    correlation_type: str
    correlation_value: float
    strength: str
    lag_days: int
    causal_direction: Optional[str]
    insight: Optional[str]
    is_actionable: bool


class CorrelationDetectionRequest(BaseModel):
    """Request parameters for correlation detection."""
    days: int = 60  # Number of days to analyze
    include_granger: bool = True  # Run Granger causality tests
    include_pearson: bool = True  # Run Pearson/Spearman
    include_cross_correlation: bool = True  # Run time-lagged tests
    include_mutual_info: bool = True  # Run mutual information
    generate_insights: bool = True  # Generate AI insights
    min_confidence: float = 0.3  # Minimum confidence to save
    include_population_comparison: bool = True  # Compare to population


class CorrelationDetectionResult(BaseModel):
    """Result of correlation detection."""
    total_correlations: int
    significant_correlations: int
    actionable_count: int
    new_correlations: int
    by_type: Dict[str, int]
    by_strength: Dict[str, int]
    top_findings: List[str]
    correlations: List[CorrelationResponse]


class CorrelationInsight(BaseModel):
    """AI-generated insight about a correlation."""
    metric_pair: str
    finding: str
    recommendation: str
    strength: str
    evidence: str
    confidence: float


class CorrelationInsightsResponse(BaseModel):
    """Response for correlation insights endpoint."""
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    total_correlations: int
    actionable_count: int
    period_days: int
    generated_at: datetime


class TopCorrelationsResponse(BaseModel):
    """Response for top correlations endpoint."""
    correlations: List[CorrelationSummary]
    total_actionable: int
