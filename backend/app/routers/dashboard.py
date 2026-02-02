from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from app.database import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse, HealthScore, HealthScoreDetailed, HealthScoreBreakdown, ScoreFactorDetail
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
    import pandas as pd
    
    # Need at least 4 days to calculate a meaningful trend
    if len(df) < 4:
        return "stable"
    
    # Compare first half vs second half
    midpoint = len(df) // 2
    first_half = df.iloc[:midpoint]
    second_half = df.iloc[midpoint:]
    
    improvements = 0
    declines = 0
    
    # Check sleep (more sleep is generally better, up to a point)
    if 'sleep_hours' in df.columns:
        first_sleep = first_half['sleep_hours'].mean()
        second_sleep = second_half['sleep_hours'].mean()
        if pd.notna(first_sleep) and pd.notna(second_sleep) and first_sleep > 0:
            change_pct = (second_sleep - first_sleep) / first_sleep
            if change_pct > 0.03:  # 3% improvement
                improvements += 1
            elif change_pct < -0.03:  # 3% decline
                declines += 1
    
    # Check sleep quality
    if 'sleep_quality' in df.columns:
        first_quality = first_half['sleep_quality'].mean()
        second_quality = second_half['sleep_quality'].mean()
        if pd.notna(first_quality) and pd.notna(second_quality) and first_quality > 0:
            change_pct = (second_quality - first_quality) / first_quality
            if change_pct > 0.05:
                improvements += 1
            elif change_pct < -0.05:
                declines += 1
    
    # Check exercise (more is generally better)
    if 'exercise_minutes' in df.columns:
        first_exercise = first_half['exercise_minutes'].sum()
        second_exercise = second_half['exercise_minutes'].sum()
        if pd.notna(first_exercise) and pd.notna(second_exercise):
            if first_exercise > 0:
                change_pct = (second_exercise - first_exercise) / first_exercise
                if change_pct > 0.05:
                    improvements += 1
                elif change_pct < -0.05:
                    declines += 1
            elif second_exercise > 0:
                # Started exercising when there was none before
                improvements += 1
    
    # Check resting HR (lower is generally better)
    if 'resting_hr' in df.columns:
        first_hr = first_half['resting_hr'].mean()
        second_hr = second_half['resting_hr'].mean()
        if pd.notna(first_hr) and pd.notna(second_hr) and first_hr > 0:
            change_pct = (second_hr - first_hr) / first_hr
            if change_pct < -0.02:  # HR decreased (improvement)
                improvements += 1
            elif change_pct > 0.02:  # HR increased (decline)
                declines += 1
    
    # Check HRV (higher is generally better - indicates better recovery)
    if 'hrv' in df.columns:
        first_hrv = first_half['hrv'].mean()
        second_hrv = second_half['hrv'].mean()
        if pd.notna(first_hrv) and pd.notna(second_hrv) and first_hrv > 0:
            change_pct = (second_hrv - first_hrv) / first_hrv
            if change_pct > 0.05:  # HRV increased (improvement)
                improvements += 1
            elif change_pct < -0.05:  # HRV decreased (decline)
                declines += 1
    
    # Check nutrition balance (moderate change threshold)
    if 'total_calories' in df.columns:
        first_cal = first_half['total_calories'].mean()
        second_cal = second_half['total_calories'].mean()
        # If calories are more consistent (less variance), that's good
        first_var = first_half['total_calories'].std() if len(first_half) > 1 else 0
        second_var = second_half['total_calories'].std() if len(second_half) > 1 else 0
        if pd.notna(first_var) and pd.notna(second_var) and first_var > 0:
            if second_var < first_var * 0.8:  # More consistent
                improvements += 1
            elif second_var > first_var * 1.2:  # Less consistent
                declines += 1
    
    if improvements > declines:
        return "improving"
    elif declines > improvements:
        return "declining"
    else:
        return "stable"


@router.get("/health-score/detailed", response_model=HealthScoreDetailed)
async def get_detailed_health_score(
    days: int = Query(30, ge=7, le=90, description="Period to calculate score"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed health score with factor breakdown.
    
    Returns:
    - Overall score with detailed breakdown by category
    - Specific factors contributing to each score
    - Comparison to previous period
    - Actionable insights
    """
    feature_eng = FeatureEngineer(db, current_user.id)
    anomaly_service = AnomalyService(db)
    
    # Get current period data
    df = await feature_eng.build_daily_feature_matrix(days=days)
    baselines = await feature_eng.get_user_baselines(days=30)
    anomaly_summary = await anomaly_service.get_anomaly_summary(current_user.id, days)
    
    # Get previous period data for comparison
    df_prev = await feature_eng.build_daily_feature_matrix(days=days*2)
    if len(df_prev) > days:
        df_prev = df_prev.iloc[:-days]  # Get only previous period
    
    if df.empty:
        return HealthScoreDetailed(
            overall_score=0,
            breakdown=HealthScoreBreakdown(
                sleep=ScoreFactorDetail(score=0, factors=["No data available"]),
                nutrition=ScoreFactorDetail(score=0, factors=["No data available"]),
                activity=ScoreFactorDetail(score=0, factors=["No data available"]),
                vitals=ScoreFactorDetail(score=0, factors=["No data available"])
            ),
            trend="unknown",
            insights=["Start logging your health data to see your score!"],
            computed_at=datetime.utcnow()
        )
    
    # Calculate detailed scores
    sleep_result = _calculate_sleep_score_detailed(df, baselines)
    nutrition_result = _calculate_nutrition_score_detailed(df, baselines)
    activity_result = _calculate_activity_score_detailed(df, baselines)
    vitals_result = _calculate_vitals_score_detailed(df, baselines, anomaly_summary)
    
    # Calculate overall
    overall = int(
        sleep_result["score"] * 0.25 +
        nutrition_result["score"] * 0.25 +
        activity_result["score"] * 0.25 +
        vitals_result["score"] * 0.25
    )
    
    # Calculate trend
    trend = _calculate_trend(df)
    
    # Calculate comparison to previous period
    comparison = None
    if not df_prev.empty and len(df_prev) >= 7:
        prev_sleep = _calculate_sleep_score(df_prev, baselines)
        prev_nutrition = _calculate_nutrition_score(df_prev, baselines)
        prev_activity = _calculate_activity_score(df_prev, baselines)
        prev_vitals = _calculate_vitals_score(df_prev, baselines, {})
        prev_overall = int((prev_sleep + prev_nutrition + prev_activity + prev_vitals) / 4)
        comparison = overall - prev_overall
    
    # Determine improvement and strength areas
    scores = {
        "sleep": sleep_result["score"],
        "nutrition": nutrition_result["score"],
        "activity": activity_result["score"],
        "vitals": vitals_result["score"]
    }
    
    top_strength = max(scores, key=scores.get)
    top_improvement = min(scores, key=scores.get)
    
    # Generate insights
    insights = _generate_health_insights(
        sleep_result, nutrition_result, activity_result, vitals_result, trend
    )
    
    return HealthScoreDetailed(
        overall_score=overall,
        breakdown=HealthScoreBreakdown(
            sleep=ScoreFactorDetail(
                score=sleep_result["score"],
                factors=sleep_result["factors"],
                key_metric="avg_sleep_hours",
                key_value=sleep_result.get("key_value")
            ),
            nutrition=ScoreFactorDetail(
                score=nutrition_result["score"],
                factors=nutrition_result["factors"],
                key_metric="avg_daily_calories",
                key_value=nutrition_result.get("key_value")
            ),
            activity=ScoreFactorDetail(
                score=activity_result["score"],
                factors=activity_result["factors"],
                key_metric="weekly_exercise_minutes",
                key_value=activity_result.get("key_value")
            ),
            vitals=ScoreFactorDetail(
                score=vitals_result["score"],
                factors=vitals_result["factors"],
                key_metric="avg_resting_hr",
                key_value=vitals_result.get("key_value")
            )
        ),
        trend=trend,
        comparison_to_last_week=comparison,
        top_improvement_area=top_improvement,
        top_strength_area=top_strength,
        insights=insights,
        computed_at=datetime.utcnow()
    )


def _calculate_sleep_score_detailed(df, baselines) -> dict:
    """Calculate detailed sleep score with factors"""
    if 'sleep_hours' not in df.columns:
        return {"score": 50, "factors": ["No sleep data available"]}
    
    sleep_data = df['sleep_hours'].dropna()
    if len(sleep_data) == 0:
        return {"score": 50, "factors": ["No sleep data available"]}
    
    factors = []
    avg_sleep = sleep_data.mean()
    std = sleep_data.std() if len(sleep_data) > 1 else 0
    
    # Duration scoring
    if 7 <= avg_sleep <= 9:
        base_score = 90
        factors.append(f"Duration: +15 (optimal {avg_sleep:.1f}h avg)")
    elif 6 <= avg_sleep <= 10:
        base_score = 70
        factors.append(f"Duration: +5 (adequate {avg_sleep:.1f}h avg)")
    else:
        base_score = 50
        direction = "low" if avg_sleep < 7 else "high"
        factors.append(f"Duration: -10 ({direction} at {avg_sleep:.1f}h avg)")
    
    # Consistency scoring
    if std < 0.5:
        consistency_bonus = 10
        factors.append("Consistency: +10 (very consistent)")
    elif std < 1.0:
        consistency_bonus = 5
        factors.append("Consistency: +5 (fairly consistent)")
    else:
        consistency_bonus = 0
        factors.append("Consistency: +0 (variable)")
    
    # Quality if available
    if 'sleep_quality' in df.columns:
        quality_data = df['sleep_quality'].dropna()
        if len(quality_data) > 0:
            avg_quality = quality_data.mean()
            if avg_quality >= 70:
                factors.append(f"Quality: +5 ({avg_quality:.0f}/100 avg)")
                base_score += 5
            elif avg_quality < 50:
                factors.append(f"Quality: -5 ({avg_quality:.0f}/100 avg)")
                base_score -= 5
    
    return {
        "score": min(100, base_score + consistency_bonus),
        "factors": factors,
        "key_value": round(avg_sleep, 2)
    }


def _calculate_nutrition_score_detailed(df, baselines) -> dict:
    """Calculate detailed nutrition score with factors"""
    if 'total_calories' not in df.columns:
        return {"score": 50, "factors": ["No nutrition data available"]}
    
    cal_data = df['total_calories'].dropna()
    if len(cal_data) == 0:
        return {"score": 50, "factors": ["No nutrition data available"]}
    
    factors = []
    avg_calories = cal_data.mean()
    
    # Calorie scoring
    if 1600 <= avg_calories <= 2500:
        base_score = 80
        factors.append(f"Calories: +10 (balanced at {avg_calories:.0f}/day)")
    elif 1400 <= avg_calories <= 3000:
        base_score = 60
        factors.append(f"Calories: +0 ({avg_calories:.0f}/day)")
    else:
        base_score = 40
        factors.append(f"Calories: -10 ({avg_calories:.0f}/day - out of range)")
    
    # Protein ratio
    if 'protein_ratio' in df.columns:
        protein_ratio = df['protein_ratio'].dropna().mean()
        if protein_ratio and protein_ratio >= 0.2:
            base_score += 10
            factors.append(f"Protein: +10 (excellent {protein_ratio*100:.0f}%)")
        elif protein_ratio and protein_ratio >= 0.15:
            base_score += 5
            factors.append(f"Protein: +5 (adequate {protein_ratio*100:.0f}%)")
        elif protein_ratio:
            factors.append(f"Protein: +0 (low at {protein_ratio*100:.0f}%)")
    
    # Sugar check
    if 'total_sugar' in df.columns:
        sugar_data = df['total_sugar'].dropna()
        if len(sugar_data) > 0:
            avg_sugar = sugar_data.mean()
            if avg_sugar < 50:
                factors.append(f"Sugar: +5 (well controlled)")
                base_score += 5
            elif avg_sugar > 100:
                factors.append(f"Sugar: -5 (high at {avg_sugar:.0f}g/day)")
                base_score -= 5
    
    return {
        "score": min(100, max(0, base_score)),
        "factors": factors,
        "key_value": round(avg_calories, 0)
    }


def _calculate_activity_score_detailed(df, baselines) -> dict:
    """Calculate detailed activity score with factors"""
    if 'exercise_minutes' not in df.columns:
        return {"score": 50, "factors": ["No exercise data available"]}
    
    exercise_data = df['exercise_minutes'].fillna(0)
    total_days = len(exercise_data)
    active_days = (exercise_data > 0).sum()
    weekly_minutes = exercise_data.sum() / (total_days / 7) if total_days > 0 else 0
    
    factors = []
    
    # WHO recommends 150 min/week moderate exercise
    if weekly_minutes >= 150:
        base_score = 90
        factors.append(f"Volume: +20 ({weekly_minutes:.0f} min/week - excellent)")
    elif weekly_minutes >= 100:
        base_score = 70
        factors.append(f"Volume: +10 ({weekly_minutes:.0f} min/week - good)")
    elif weekly_minutes >= 50:
        base_score = 50
        factors.append(f"Volume: +0 ({weekly_minutes:.0f} min/week - moderate)")
    else:
        base_score = 30
        factors.append(f"Volume: -10 ({weekly_minutes:.0f} min/week - low)")
    
    # Consistency bonus
    consistency_pct = active_days / total_days if total_days > 0 else 0
    if consistency_pct >= 0.6:
        consistency_bonus = 10
        factors.append(f"Consistency: +10 ({active_days}/{total_days} days active)")
    elif consistency_pct >= 0.4:
        consistency_bonus = 5
        factors.append(f"Consistency: +5 ({active_days}/{total_days} days active)")
    else:
        consistency_bonus = 0
        factors.append(f"Consistency: +0 ({active_days}/{total_days} days active)")
    
    return {
        "score": min(100, base_score + consistency_bonus),
        "factors": factors,
        "key_value": round(weekly_minutes, 0)
    }


def _calculate_vitals_score_detailed(df, baselines, anomaly_summary) -> dict:
    """Calculate detailed vitals score with factors"""
    factors = []
    base_score = 80
    
    # Anomaly penalty
    high_anomalies = anomaly_summary.get('by_severity', {}).get('high', 0)
    medium_anomalies = anomaly_summary.get('by_severity', {}).get('medium', 0)
    
    if high_anomalies > 0:
        penalty = high_anomalies * 5
        base_score -= penalty
        factors.append(f"Anomalies: -{penalty} ({high_anomalies} high severity)")
    if medium_anomalies > 0:
        penalty = medium_anomalies * 2
        base_score -= penalty
        factors.append(f"Anomalies: -{penalty} ({medium_anomalies} medium severity)")
    if high_anomalies == 0 and medium_anomalies == 0:
        factors.append("Anomalies: +5 (none detected)")
        base_score += 5
    
    key_value = None
    
    # Heart rate
    if 'resting_hr' in df.columns:
        hr_data = df['resting_hr'].dropna()
        if len(hr_data) > 0:
            avg_hr = hr_data.mean()
            key_value = round(avg_hr, 1)
            if 50 <= avg_hr <= 70:
                base_score += 10
                factors.append(f"Resting HR: +10 (optimal at {avg_hr:.0f} bpm)")
            elif 50 <= avg_hr <= 80:
                base_score += 5
                factors.append(f"Resting HR: +5 (good at {avg_hr:.0f} bpm)")
            else:
                factors.append(f"Resting HR: +0 ({avg_hr:.0f} bpm)")
    
    # HRV if available
    if 'hrv_ms' in df.columns:
        hrv_data = df['hrv_ms'].dropna()
        if len(hrv_data) > 0:
            avg_hrv = hrv_data.mean()
            if avg_hrv >= 50:
                factors.append(f"HRV: +5 (good at {avg_hrv:.0f}ms)")
                base_score += 5
            elif avg_hrv < 30:
                factors.append(f"HRV: -5 (low at {avg_hrv:.0f}ms)")
                base_score -= 5
    
    return {
        "score": max(30, min(100, base_score)),
        "factors": factors,
        "key_value": key_value
    }


def _generate_health_insights(sleep, nutrition, activity, vitals, trend) -> list:
    """Generate actionable health insights"""
    insights = []
    
    # Sleep insights
    if sleep["score"] < 60:
        insights.append("Your sleep score is below optimal. Focus on consistent bedtimes and 7-8 hours of sleep.")
    elif sleep["score"] >= 85:
        insights.append("Excellent sleep habits! Your consistent rest is boosting your overall health.")
    
    # Activity insights
    if activity["score"] < 50:
        insights.append("Consider increasing your activity. Even 30 minutes of walking daily can make a big difference.")
    elif activity["score"] >= 80:
        insights.append("Great activity level! You're meeting or exceeding exercise recommendations.")
    
    # Nutrition insights
    if nutrition["score"] < 60:
        insights.append("Your nutrition could use attention. Focus on balanced meals and adequate protein.")
    
    # Vitals insights
    if vitals["score"] < 60:
        insights.append("Some vital signs show anomalies. Consider reviewing your recent data or consulting a professional.")
    
    # Trend insight
    if trend == "improving":
        insights.append("Your health metrics are trending upward. Keep up the good work!")
    elif trend == "declining":
        insights.append("Some metrics have declined recently. Consider reviewing your habits.")
    
    # Ensure we have at least one insight
    if not insights:
        insights.append("Your health metrics are stable. Continue your current healthy habits!")
    
    return insights[:4]  # Limit to 4 insights
