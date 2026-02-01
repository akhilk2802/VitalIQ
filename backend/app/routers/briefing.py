"""
Morning Briefing API

Aggregates predictions and recommendations into a single daily briefing.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional
from datetime import date, datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.utils.security import get_current_user
from app.ml.prediction.recovery import RecoveryPredictor
from app.ml.prediction.cravings import CravingsPredictor
from app.schemas.briefing import (
    MorningBriefingResponse, 
    RecoveryBrief, 
    CravingsBrief,
    RecommendationItem,
    AnomalySummary,
    CorrelationWatch
)
from app.schemas.prediction import RecoveryResponse, CravingsForecastResponse
from app.services.recommendation_service import RecommendationService

router = APIRouter()


@router.get("/today", response_model=MorningBriefingResponse)
async def get_morning_briefing(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's morning briefing with predictions and recommendations.
    
    Includes:
    - Recovery readiness prediction
    - Food craving forecast
    - Personalized recommendations
    - Yesterday's anomaly summary
    - Key correlations to watch
    """
    target_date = date.today()
    
    # Get recovery prediction
    recovery_predictor = RecoveryPredictor(db, current_user.id)
    recovery_result = await recovery_predictor.predict(target_date)
    
    # Get cravings prediction
    cravings_predictor = CravingsPredictor(db, current_user.id)
    cravings_result = await cravings_predictor.predict(target_date)
    
    # Get yesterday's anomalies
    yesterday = target_date - timedelta(days=1)
    anomaly_result = await db.execute(
        select(Anomaly)
        .where(and_(
            Anomaly.user_id == current_user.id,
            Anomaly.date == yesterday
        ))
        .order_by(Anomaly.detected_at.desc())
    )
    anomalies = anomaly_result.scalars().all()
    
    # Get top correlations
    correlation_result = await db.execute(
        select(Correlation)
        .where(and_(
            Correlation.user_id == current_user.id,
            Correlation.is_actionable == True
        ))
        .order_by(Correlation.confidence_score.desc())
        .limit(3)
    )
    correlations = correlation_result.scalars().all()
    
    # Build briefing components
    recovery_brief = RecoveryBrief(
        score=recovery_result.score,
        status=recovery_result.status,
        message=recovery_result.message,
        top_factor=_get_top_factor(recovery_result.factors)
    )
    
    cravings_brief = CravingsBrief(
        primary_type=cravings_result.primary_craving.craving_type,
        risk_level=cravings_result.overall_risk,
        reasoning=cravings_result.primary_craving.reasoning,
        countermeasures=cravings_result.primary_craving.countermeasures[:3],
        peak_time=cravings_result.primary_craving.peak_time
    )
    
    # Generate recommendations
    recommendations = _generate_recommendations(
        recovery_result, 
        cravings_result,
        anomalies,
        correlations
    )
    
    # Anomaly summary
    anomaly_summary = AnomalySummary(
        count=len(anomalies),
        most_recent=anomalies[0].metric_name if anomalies else None,
        severity=anomalies[0].severity.value if anomalies else None
    )
    
    # Correlation watches
    correlation_watches = [
        CorrelationWatch(
            metrics=f"{c.metric_a} → {c.metric_b}",
            insight=c.insight or f"Strong {c.strength.value} correlation"
        )
        for c in correlations[:2]
    ]
    
    # Generate greeting
    greeting = _generate_greeting(recovery_result.score, target_date)
    
    # Calculate overall confidence
    confidence = (recovery_result.confidence + 0.7) / 2  # Blend with default
    
    return MorningBriefingResponse(
        date=target_date,
        greeting=greeting,
        recovery=recovery_brief,
        cravings=cravings_brief,
        recommendations=recommendations,
        anomalies_yesterday=anomaly_summary,
        correlations_to_watch=correlation_watches,
        health_score=None,  # Would need separate calculation
        generated_at=datetime.utcnow(),
        confidence=confidence
    )


@router.get("/recovery", response_model=RecoveryResponse)
async def get_recovery_prediction(
    target_date: Optional[date] = Query(None, description="Date to predict for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed recovery readiness prediction"""
    predictor = RecoveryPredictor(db, current_user.id)
    result = await predictor.predict(target_date)
    return RecoveryResponse(**result.to_dict())


@router.get("/cravings", response_model=CravingsForecastResponse)
async def get_cravings_forecast(
    target_date: Optional[date] = Query(None, description="Date to predict for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed food cravings forecast"""
    predictor = CravingsPredictor(db, current_user.id)
    result = await predictor.predict(target_date)
    return CravingsForecastResponse(**result.to_dict())


def _get_top_factor(factors: dict) -> Optional[str]:
    """Get the factor with lowest score (most limiting)"""
    if not factors:
        return None
    return min(factors, key=factors.get)


def _generate_greeting(recovery_score: int, target_date: date) -> str:
    """Generate personalized greeting based on recovery"""
    day_name = target_date.strftime("%A")
    
    if recovery_score >= 8:
        return f"Good morning! You're in great shape this {day_name}. 💪"
    elif recovery_score >= 6:
        return f"Good morning! Here's your health forecast for {day_name}."
    elif recovery_score >= 4:
        return f"Good morning. Your body could use some extra care today."
    else:
        return f"Good morning. Consider making today a recovery day."


def _generate_recommendations(
    recovery,
    cravings,
    anomalies,
    correlations
) -> list:
    """Generate prioritized recommendations based on all predictions"""
    recommendations = []
    
    # Recovery-based exercise recommendation
    if recovery.score >= 8:
        recommendations.append(RecommendationItem(
            type="exercise",
            priority="high",
            message="Perfect day for an intense workout or long run",
            reasoning="Your recovery score is excellent"
        ))
    elif recovery.score >= 6:
        recommendations.append(RecommendationItem(
            type="exercise",
            priority="medium",
            message="30-45 min moderate workout recommended",
            reasoning="Good recovery supports moderate activity"
        ))
    elif recovery.score >= 4:
        recommendations.append(RecommendationItem(
            type="exercise",
            priority="low",
            message="Light activity like walking or yoga today",
            reasoning="Your body needs lighter activity"
        ))
    else:
        recommendations.append(RecommendationItem(
            type="wellness",
            priority="high",
            message="Focus on rest and recovery today",
            reasoning="Your recovery score suggests you need rest"
        ))
    
    # Craving-based nutrition recommendation
    if cravings.overall_risk in ["moderate", "high"]:
        primary = cravings.primary_craving
        recommendations.append(RecommendationItem(
            type="nutrition",
            priority="high" if cravings.overall_risk == "high" else "medium",
            message=primary.countermeasures[0] if primary.countermeasures else "Plan healthy snacks",
            reasoning=f"Expecting {primary.craving_type} cravings around {primary.peak_time or 'afternoon'}"
        ))
    
    # Sleep recommendation if poor sleep detected
    if recovery.factors.get("sleep_quality", 10) < 5 or recovery.factors.get("sleep_duration", 10) < 5:
        recommendations.append(RecommendationItem(
            type="sleep",
            priority="medium",
            message="Aim for 7-9 hours tonight; avoid screens 1hr before bed",
            reasoning="Your sleep metrics could use improvement"
        ))
    
    # Correlation-based recommendations
    for corr in correlations[:1]:  # Top correlation
        if corr.recommendation:
            recommendations.append(RecommendationItem(
                type="wellness",
                priority="low",
                message=corr.recommendation,
                reasoning=f"Based on your {corr.metric_a} ↔ {corr.metric_b} pattern"
            ))
    
    # Anomaly-based recommendation
    if anomalies:
        high_severity = [a for a in anomalies if a.severity.value == "high"]
        if high_severity:
            recommendations.append(RecommendationItem(
                type="wellness",
                priority="high",
                message=f"Review yesterday's {high_severity[0].metric_name.replace('_', ' ')} reading",
                reasoning="A significant anomaly was detected"
            ))
    
    # Sort by priority and limit
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: priority_order.get(r.priority, 2))
    
    return recommendations[:5]


@router.get("/recommendations")
async def get_recommendations(
    days: int = Query(7, ge=1, le=30, description="Days of data to analyze"),
    include_ai: bool = Query(True, description="Include AI-powered recommendations"),
    max_items: int = Query(8, ge=1, le=15, description="Maximum recommendations"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized health recommendations.
    
    Combines:
    - Rule-based recommendations from health patterns
    - Correlation-based insights
    - AI-generated personalized advice
    """
    service = RecommendationService(db, current_user.id)
    recommendations = await service.get_recommendations(
        days=days,
        include_ai=include_ai,
        max_recommendations=max_items
    )
    
    return {
        "count": len(recommendations),
        "recommendations": [r.to_dict() for r in recommendations]
    }
