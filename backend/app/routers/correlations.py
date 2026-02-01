"""
Correlation API endpoints.

Provides endpoints for:
- Detecting correlations between health metrics
- Retrieving saved correlations
- Getting top actionable insights
- AI-generated correlation explanations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.models.user import User
from app.schemas.correlation import (
    CorrelationResponse, CorrelationSummary, CorrelationDetectionRequest,
    CorrelationDetectionResult, CorrelationInsightsResponse, TopCorrelationsResponse
)
from app.services.correlation_service import CorrelationService
from app.services.insights_service import InsightsService
from app.utils.security import get_current_user
from app.utils.enums import CorrelationType

router = APIRouter()


@router.get("", response_model=List[CorrelationResponse])
async def get_correlations(
    correlation_type: Optional[CorrelationType] = Query(None, description="Filter by correlation type"),
    actionable_only: bool = Query(False, description="Only return actionable correlations"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detected correlations for the current user.
    
    Returns correlations ordered by confidence score.
    """
    service = CorrelationService(db)
    correlations = await service.get_correlations(
        user_id=current_user.id,
        correlation_type=correlation_type,
        actionable_only=actionable_only,
        limit=limit
    )
    return correlations


@router.post("/detect", response_model=CorrelationDetectionResult)
async def detect_correlations(
    request: CorrelationDetectionRequest = CorrelationDetectionRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger correlation detection for the current user.
    
    Runs multiple correlation detection algorithms:
    - **Pearson/Spearman**: Linear and monotonic same-day correlations
    - **Cross-correlation**: Time-lagged relationships (e.g., exercise today → sleep tomorrow)
    - **Granger Causality**: Predictive/causal relationships
    - **Mutual Information**: Non-linear dependencies
    
    Optionally compares results against population baselines.
    """
    service = CorrelationService(db)
    
    # Run detection
    results = await service.detect_correlations(
        user=current_user,
        days=request.days,
        include_granger=request.include_granger,
        include_pearson=request.include_pearson,
        include_cross_correlation=request.include_cross_correlation,
        include_mutual_info=request.include_mutual_info,
        include_population_comparison=request.include_population_comparison,
        min_confidence=request.min_confidence,
        save_results=True
    )
    
    # Get all correlations for response
    all_correlations = await service.get_correlations(
        user_id=current_user.id,
        limit=100
    )
    
    # Generate insights if requested
    if request.generate_insights and all_correlations:
        insights_service = InsightsService()
        # Update top correlations with AI insights
        for corr in all_correlations[:10]:  # Limit to top 10 for speed
            if not corr.insight:
                insight_data = await insights_service.generate_correlation_insight(corr)
                if insight_data:
                    corr.insight = insight_data.get('insight')
                    corr.recommendation = insight_data.get('recommendation')
        await db.flush()
    
    # Build summary
    by_type = {}
    by_strength = {}
    for r in results:
        type_name = r.correlation_type.value
        by_type[type_name] = by_type.get(type_name, 0) + 1
        
        strength = r.strength.value
        by_strength[strength] = by_strength.get(strength, 0) + 1
    
    # Generate top findings
    top_findings = []
    for r in results[:5]:
        if r.causal_direction and r.causal_direction.value != 'none':
            finding = f"{r.metric_a} predicts {r.metric_b} (lag: {r.lag_days} day)"
        elif r.lag_days > 0:
            finding = f"{r.metric_a} affects {r.metric_b} after {r.lag_days} day(s)"
        else:
            direction = "positively" if r.correlation_value > 0 else "negatively"
            finding = f"{r.metric_a} and {r.metric_b} are {direction} correlated"
        top_findings.append(finding)
    
    return CorrelationDetectionResult(
        total_correlations=len(all_correlations),
        significant_correlations=sum(1 for c in all_correlations if c.is_significant),
        actionable_count=sum(1 for c in all_correlations if c.is_actionable),
        new_correlations=len(results),
        by_type=by_type,
        by_strength=by_strength,
        top_findings=top_findings,
        correlations=[CorrelationResponse.model_validate(c) for c in all_correlations[:50]]
    )


@router.get("/top", response_model=TopCorrelationsResponse)
async def get_top_correlations(
    limit: int = Query(5, ge=1, le=20, description="Number of top correlations"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top actionable correlations for dashboard display.
    
    Returns the most significant, actionable correlations in a lightweight format.
    """
    service = CorrelationService(db)
    
    correlations = await service.get_top_actionable(
        user_id=current_user.id,
        limit=limit
    )
    
    # Get total actionable count
    all_actionable = await service.get_correlations(
        user_id=current_user.id,
        actionable_only=True,
        limit=200
    )
    
    summaries = [
        CorrelationSummary(
            metric_a=c.metric_a,
            metric_b=c.metric_b,
            correlation_type=c.correlation_type.value,
            correlation_value=c.correlation_value,
            strength=c.strength.value,
            lag_days=c.lag_days,
            causal_direction=c.causal_direction.value if c.causal_direction else None,
            insight=c.insight,
            is_actionable=c.is_actionable
        )
        for c in correlations
    ]
    
    return TopCorrelationsResponse(
        correlations=summaries,
        total_actionable=len(all_actionable)
    )


@router.get("/insights", response_model=CorrelationInsightsResponse)
async def get_correlation_insights(
    days: int = Query(30, ge=7, le=90, description="Period to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-generated insights based on detected correlations.
    
    Analyzes correlation patterns and provides:
    - Summary of health relationships
    - Key findings about metric interactions
    - Actionable recommendations
    """
    service = CorrelationService(db)
    insights_service = InsightsService()
    
    # Get correlations
    correlations = await service.get_correlations(
        user_id=current_user.id,
        limit=50
    )
    
    if not correlations:
        return CorrelationInsightsResponse(
            summary="No correlations detected yet. Generate mock data and run correlation detection first.",
            key_findings=[],
            recommendations=["Log at least 14 days of health data to enable correlation analysis"],
            total_correlations=0,
            actionable_count=0,
            period_days=days,
            generated_at=datetime.utcnow()
        )
    
    # Generate insights
    insights = await insights_service.generate_correlation_insights(correlations, days)
    
    return CorrelationInsightsResponse(
        summary=insights.get('summary', 'Analysis complete.'),
        key_findings=insights.get('key_findings', []),
        recommendations=insights.get('recommendations', []),
        total_correlations=len(correlations),
        actionable_count=sum(1 for c in correlations if c.is_actionable),
        period_days=days,
        generated_at=datetime.utcnow()
    )


@router.get("/summary")
async def get_correlation_summary(
    days: int = Query(30, ge=1, le=365, description="Period to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get summary statistics about detected correlations."""
    service = CorrelationService(db)
    return await service.get_correlation_summary(current_user.id, days)


# IMPORTANT: Dynamic route must come LAST to avoid matching static paths like /summary, /insights
@router.get("/{correlation_id}", response_model=CorrelationResponse)
async def get_correlation(
    correlation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific correlation by ID."""
    service = CorrelationService(db)
    
    correlation = await service.get_correlation_by_id(
        user_id=current_user.id,
        correlation_id=correlation_id
    )
    
    if not correlation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correlation not found"
        )
    
    return correlation
