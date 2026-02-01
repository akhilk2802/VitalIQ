"""Schemas for morning briefing API"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date, datetime


class RecoveryBrief(BaseModel):
    """Recovery section of morning briefing"""
    score: int = Field(..., ge=1, le=10, description="Recovery score 1-10")
    status: str = Field(..., description="Recovery status")
    message: str = Field(..., description="Recovery message")
    top_factor: Optional[str] = Field(None, description="Most impactful factor")


class CravingsBrief(BaseModel):
    """Cravings section of morning briefing"""
    primary_type: str = Field(..., description="Primary craving type")
    risk_level: str = Field(..., description="Risk level: low, moderate, high")
    reasoning: str = Field(..., description="Brief reasoning")
    countermeasures: List[str] = Field(..., description="Top countermeasures")
    peak_time: Optional[str] = Field(None, description="Peak craving time")


class RecommendationItem(BaseModel):
    """Single recommendation"""
    type: str = Field(..., description="Type: exercise, nutrition, sleep, wellness")
    priority: str = Field(..., description="Priority: high, medium, low")
    message: str = Field(..., description="Recommendation message")
    reasoning: Optional[str] = Field(None, description="Why this recommendation")


class CorrelationWatch(BaseModel):
    """Correlation to watch"""
    metrics: str = Field(..., description="Metric pair, e.g., 'sleep → energy'")
    insight: str = Field(..., description="Brief insight")


class AnomalySummary(BaseModel):
    """Anomaly summary for briefing"""
    count: int = Field(..., description="Number of anomalies")
    most_recent: Optional[str] = Field(None, description="Most recent anomaly metric")
    severity: Optional[str] = Field(None, description="Highest severity")


class MorningBriefingResponse(BaseModel):
    """Complete morning briefing response"""
    briefing_date: date = Field(..., description="Briefing date")
    greeting: str = Field(..., description="Personalized greeting")
    
    # Core predictions
    recovery: RecoveryBrief
    cravings: CravingsBrief
    
    # Recommendations
    recommendations: List[RecommendationItem] = Field(..., description="Today's recommendations")
    
    # Context
    anomalies_yesterday: AnomalySummary
    correlations_to_watch: List[CorrelationWatch] = Field(default_factory=list)
    
    # Health score
    health_score: Optional[int] = Field(None, description="Current health score if available")
    
    # Meta
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence in predictions")
    
    class Config:
        json_schema_extra = {
            "example": {
                "briefing_date": "2026-02-01",
                "greeting": "Good morning! Here's your health forecast for today.",
                "recovery": {
                    "score": 7,
                    "status": "ready_for_moderate",
                    "message": "Good recovery. You're ready for moderate activity.",
                    "top_factor": "sleep_quality"
                },
                "cravings": {
                    "primary_type": "sugar",
                    "risk_level": "moderate",
                    "reasoning": "5.5hr sleep may trigger energy cravings",
                    "countermeasures": ["Have protein-rich breakfast", "Prepare healthy snacks"],
                    "peak_time": "2-4 PM"
                },
                "recommendations": [
                    {
                        "type": "exercise",
                        "priority": "medium",
                        "message": "30-40 min moderate workout recommended",
                        "reasoning": "Recovery score supports moderate activity"
                    }
                ],
                "anomalies_yesterday": {"count": 0, "most_recent": None, "severity": None},
                "correlations_to_watch": [
                    {"metrics": "sleep → recovery", "insight": "Your sleep quality predicts next-day energy"}
                ],
                "health_score": 75,
                "confidence": 0.85
            }
        }
