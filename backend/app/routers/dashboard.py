from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, HealthScore
from app.services.metrics_service import MetricsService
from app.services.anomaly_service import AnomalyService
from app.ml.feature_engineering import FeatureEngineer
from app.utils.security import get_current_user
from datetime import datetime

router = APIRouter()


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    days: int = Query(7, ge=1, le=90, description="Number of days (if start_date not provided)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get unified dashboard with all health metrics.
    
    Returns daily summaries including:
    - Nutrition totals
    - Sleep data
    - Exercise activities
    - Vital signs
    - Body metrics
    - Chronic health metrics
    - Detected anomalies
    """
    service = MetricsService(db)
    
    return await service.get_dashboard(
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        days=days
    )


@router.get("/health-score", response_model=HealthScore)
async def get_health_score(
    days: int = Query(30, ge=7, le=90, description="Period to calculate score"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate an overall health score based on user's data.
    
    Score is calculated from:
    - Sleep consistency and quality
    - Nutrition balance
    - Exercise frequency
    - Vital signs stability
    - Anomaly frequency
    """
    feature_eng = FeatureEngineer(db, current_user.id)
    anomaly_service = AnomalyService(db)
    
    # Get data
    df = await feature_eng.build_daily_feature_matrix(days=days)
    baselines = await feature_eng.get_user_baselines(days=30)
    anomaly_summary = await anomaly_service.get_anomaly_summary(current_user.id, days)
    
    if df.empty:
        return HealthScore(
            overall_score=0,
            sleep_score=0,
            nutrition_score=0,
            activity_score=0,
            vitals_score=0,
            trend="unknown",
            computed_at=datetime.utcnow()
        )
    
    # Calculate component scores
    sleep_score = _calculate_sleep_score(df, baselines)
    nutrition_score = _calculate_nutrition_score(df, baselines)
    activity_score = _calculate_activity_score(df, baselines)
    vitals_score = _calculate_vitals_score(df, baselines, anomaly_summary)
    
    # Overall score (weighted average)
    overall = int(
        sleep_score * 0.25 +
        nutrition_score * 0.25 +
        activity_score * 0.25 +
        vitals_score * 0.25
    )
    
    # Determine trend
    trend = _calculate_trend(df)
    
    return HealthScore(
        overall_score=overall,
        sleep_score=sleep_score,
        nutrition_score=nutrition_score,
        activity_score=activity_score,
        vitals_score=vitals_score,
        trend=trend,
        computed_at=datetime.utcnow()
    )


def _calculate_sleep_score(df, baselines) -> int:
    """Calculate sleep health score (0-100)"""
    if 'sleep_hours' not in df.columns:
        return 50
    
    sleep_data = df['sleep_hours'].dropna()
    if len(sleep_data) == 0:
        return 50
    
    avg_sleep = sleep_data.mean()
    
    # Optimal sleep is 7-9 hours
    if 7 <= avg_sleep <= 9:
        base_score = 90
    elif 6 <= avg_sleep <= 10:
        base_score = 70
    else:
        base_score = 50
    
    # Bonus for consistency
    std = sleep_data.std()
    consistency_bonus = max(0, 10 - int(std * 5))
    
    return min(100, base_score + consistency_bonus)


def _calculate_nutrition_score(df, baselines) -> int:
    """Calculate nutrition health score (0-100)"""
    if 'total_calories' not in df.columns:
        return 50
    
    cal_data = df['total_calories'].dropna()
    if len(cal_data) == 0:
        return 50
    
    avg_calories = cal_data.mean()
    
    # Base score from calorie consistency
    if 1600 <= avg_calories <= 2500:
        base_score = 80
    elif 1400 <= avg_calories <= 3000:
        base_score = 60
    else:
        base_score = 40
    
    # Bonus for protein ratio if available
    if 'protein_ratio' in df.columns:
        protein_ratio = df['protein_ratio'].dropna().mean()
        if protein_ratio and protein_ratio >= 0.15:
            base_score += 10
    
    return min(100, base_score)


def _calculate_activity_score(df, baselines) -> int:
    """Calculate activity/exercise score (0-100)"""
    if 'exercise_minutes' not in df.columns:
        return 50
    
    exercise_data = df['exercise_minutes'].fillna(0)
    total_days = len(exercise_data)
    active_days = (exercise_data > 0).sum()
    
    # WHO recommends 150 min/week moderate exercise
    weekly_minutes = exercise_data.sum() / (total_days / 7)
    
    if weekly_minutes >= 150:
        base_score = 90
    elif weekly_minutes >= 100:
        base_score = 70
    elif weekly_minutes >= 50:
        base_score = 50
    else:
        base_score = 30
    
    # Bonus for consistency (exercising regularly)
    consistency_pct = active_days / total_days if total_days > 0 else 0
    consistency_bonus = int(consistency_pct * 10)
    
    return min(100, base_score + consistency_bonus)


def _calculate_vitals_score(df, baselines, anomaly_summary) -> int:
    """Calculate vitals health score (0-100)"""
    base_score = 80
    
    # Penalize for anomalies
    high_anomalies = anomaly_summary.get('by_severity', {}).get('high', 0)
    medium_anomalies = anomaly_summary.get('by_severity', {}).get('medium', 0)
    
    penalty = high_anomalies * 5 + medium_anomalies * 2
    score = max(30, base_score - penalty)
    
    # Check vital signs stability
    if 'resting_hr' in df.columns:
        hr_data = df['resting_hr'].dropna()
        if len(hr_data) > 0:
            avg_hr = hr_data.mean()
            if 50 <= avg_hr <= 80:
                score += 10
    
    return min(100, score)


def _calculate_trend(df) -> str:
    """Determine if health metrics are improving, stable, or declining"""
    if len(df) < 14:
        return "stable"
    
    # Compare first half vs second half
    midpoint = len(df) // 2
    first_half = df.iloc[:midpoint]
    second_half = df.iloc[midpoint:]
    
    improvements = 0
    declines = 0
    
    # Check sleep
    if 'sleep_hours' in df.columns:
        first_sleep = first_half['sleep_hours'].mean()
        second_sleep = second_half['sleep_hours'].mean()
        if first_sleep and second_sleep:
            if second_sleep > first_sleep * 1.05:
                improvements += 1
            elif second_sleep < first_sleep * 0.95:
                declines += 1
    
    # Check exercise
    if 'exercise_minutes' in df.columns:
        first_exercise = first_half['exercise_minutes'].sum()
        second_exercise = second_half['exercise_minutes'].sum()
        if second_exercise > first_exercise * 1.1:
            improvements += 1
        elif second_exercise < first_exercise * 0.9:
            declines += 1
    
    # Check resting HR (lower is generally better)
    if 'resting_hr' in df.columns:
        first_hr = first_half['resting_hr'].mean()
        second_hr = second_half['resting_hr'].mean()
        if first_hr and second_hr:
            if second_hr < first_hr * 0.95:
                improvements += 1
            elif second_hr > first_hr * 1.05:
                declines += 1
    
    if improvements > declines:
        return "improving"
    elif declines > improvements:
        return "declining"
    else:
        return "stable"
