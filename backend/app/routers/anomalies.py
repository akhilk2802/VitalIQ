from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.schemas.anomaly import (
    AnomalyResponse, AnomalyDetectionRequest, AnomalyDetectionResult,
    AnomalyAcknowledge, InsightResponse
)
from app.services.anomaly_service import AnomalyService
from app.services.insights_service import InsightsService
from app.ml.feature_engineering import FeatureEngineer
from app.utils.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[AnomalyResponse])
async def get_anomalies(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detected anomalies for the current user"""
    service = AnomalyService(db)
    anomalies = await service.get_anomalies(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        acknowledged=acknowledged,
        limit=limit,
    )
    return anomalies


@router.post("/detect", response_model=AnomalyDetectionResult)
async def detect_anomalies(
    request: AnomalyDetectionRequest = AnomalyDetectionRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger anomaly detection for the current user.
    
    Runs Z-Score and Isolation Forest detectors on historical data
    and optionally generates AI explanations for detected anomalies.
    """
    service = AnomalyService(db)
    
    # Run detection
    results = await service.detect_anomalies(
        user=current_user,
        days=request.days,
        save_results=True,
    )
    
    # Get all anomalies including newly detected
    all_anomalies = await service.get_anomalies(
        user_id=current_user.id,
        limit=100
    )
    
    # Generate explanations if requested
    if request.include_explanation and results:
        insights_service = InsightsService()
        feature_eng = FeatureEngineer(db, current_user.id)
        baselines = await feature_eng.get_user_baselines(days=30)
        
        # Update explanations for new anomalies
        for anomaly in all_anomalies:
            if not anomaly.explanation:
                explanation = await insights_service.generate_anomaly_explanation(
                    anomaly, 
                    baselines
                )
                anomaly.explanation = explanation
        
        await db.flush()
    
    return AnomalyDetectionResult(
        total_anomalies=len(all_anomalies),
        new_anomalies=len(results),
        anomalies=[AnomalyResponse.model_validate(a) for a in all_anomalies[:50]]
    )


@router.patch("/{anomaly_id}/acknowledge", response_model=AnomalyResponse)
async def acknowledge_anomaly(
    anomaly_id: uuid.UUID,
    acknowledge_data: AnomalyAcknowledge = AnomalyAcknowledge(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an anomaly as acknowledged"""
    service = AnomalyService(db)
    
    anomaly = await service.acknowledge_anomaly(
        user_id=current_user.id,
        anomaly_id=anomaly_id
    )
    
    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anomaly not found"
        )
    
    return anomaly


@router.get("/summary")
async def get_anomaly_summary(
    days: int = Query(30, ge=1, le=365, description="Period to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get summary statistics about detected anomalies"""
    service = AnomalyService(db)
    return await service.get_anomaly_summary(current_user.id, days)


@router.get("/insights", response_model=InsightResponse)
async def get_insights(
    days: int = Query(30, ge=7, le=90, description="Period to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-generated insights based on detected anomalies.
    
    Analyzes patterns across anomalies and provides:
    - Summary of health patterns
    - Key findings
    - Actionable recommendations
    """
    service = AnomalyService(db)
    insights_service = InsightsService()
    feature_eng = FeatureEngineer(db, current_user.id)
    
    # Get anomalies and baselines
    from datetime import timedelta
    start_date = date.today() - timedelta(days=days)
    
    anomalies = await service.get_anomalies(
        user_id=current_user.id,
        start_date=start_date,
        limit=50
    )
    
    baselines = await feature_eng.get_user_baselines(days=30)
    
    # Generate insights
    insights = await insights_service.generate_insights_summary(
        anomalies=anomalies,
        user_baselines=baselines,
        period_days=days
    )
    
    return insights
