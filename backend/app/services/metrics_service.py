from typing import Optional, List, Dict
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.models.food_entry import FoodEntry
from app.models.sleep_entry import SleepEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.models.body_metrics import BodyMetrics
from app.models.chronic_metrics import ChronicMetrics
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.schemas.dashboard import DailySummary, DashboardResponse, CorrelationSummaryItem
from app.schemas.food import DailyNutritionSummary, FoodEntryResponse
from app.schemas.sleep import SleepEntryResponse
from app.schemas.exercise import ExerciseEntryResponse
from app.schemas.vitals import VitalSignsResponse
from app.schemas.body import BodyMetricsResponse
from app.schemas.chronic import ChronicMetricsResponse
from app.schemas.anomaly import AnomalyResponse


class MetricsService:
    """Service for aggregating and retrieving unified health metrics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_dashboard(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: int = 7,
    ) -> DashboardResponse:
        """
        Get unified dashboard data for a user.
        
        Args:
            user_id: User's UUID
            start_date: Start date (default: today - days)
            end_date: End date (default: today)
            days: Number of days if start_date not specified
        
        Returns:
            DashboardResponse with daily summaries
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days - 1)
        
        # Generate date range
        date_range = []
        current = start_date
        while current <= end_date:
            date_range.append(current)
            current += timedelta(days=1)
        
        # Fetch all data for the period
        food_entries = await self._get_food_entries(user_id, start_date, end_date)
        sleep_entries = await self._get_sleep_entries(user_id, start_date, end_date)
        exercise_entries = await self._get_exercise_entries(user_id, start_date, end_date)
        vital_signs = await self._get_vital_signs(user_id, start_date, end_date)
        body_metrics = await self._get_body_metrics(user_id, start_date, end_date)
        chronic_metrics = await self._get_chronic_metrics(user_id, start_date, end_date)
        anomalies = await self._get_anomalies(user_id, start_date, end_date)
        
        # Group by date
        daily_summaries = []
        total_anomalies = 0
        unacknowledged = 0
        
        for day in date_range:
            # Filter entries for this day
            day_food = [f for f in food_entries if f.date == day]
            day_sleep = next((s for s in sleep_entries if s.date == day), None)
            day_exercise = [e for e in exercise_entries if e.date == day]
            day_vitals = [v for v in vital_signs if v.date == day]
            day_body = next((b for b in body_metrics if b.date == day), None)
            day_chronic = [c for c in chronic_metrics if c.date == day]
            day_anomalies = [a for a in anomalies if a.date == day]
            
            # Calculate nutrition summary
            nutrition_summary = None
            if day_food:
                nutrition_summary = DailyNutritionSummary(
                    date=day,
                    total_calories=sum(f.calories for f in day_food),
                    total_protein_g=sum(f.protein_g for f in day_food),
                    total_carbs_g=sum(f.carbs_g for f in day_food),
                    total_fats_g=sum(f.fats_g for f in day_food),
                    total_sugar_g=sum(f.sugar_g for f in day_food),
                    total_fiber_g=sum(f.fiber_g or 0 for f in day_food),
                    total_sodium_mg=sum(f.sodium_mg or 0 for f in day_food),
                    meal_count=len(day_food),
                    entries=[FoodEntryResponse.model_validate(f) for f in day_food]
                )
            
            # Count anomalies
            total_anomalies += len(day_anomalies)
            unacknowledged += sum(1 for a in day_anomalies if not a.is_acknowledged)
            
            daily_summaries.append(DailySummary(
                date=day,
                nutrition=nutrition_summary,
                sleep=SleepEntryResponse.model_validate(day_sleep) if day_sleep else None,
                exercises=[ExerciseEntryResponse.model_validate(e) for e in day_exercise],
                vitals=[VitalSignsResponse.model_validate(v) for v in day_vitals],
                body_metrics=BodyMetricsResponse.model_validate(day_body) if day_body else None,
                chronic_metrics=[ChronicMetricsResponse.model_validate(c) for c in day_chronic],
                anomalies=[AnomalyResponse.model_validate(a) for a in day_anomalies],
            ))
        
        # Get top correlations for dashboard
        top_correlations = await self._get_top_correlations(user_id, limit=5)
        correlation_summaries = [
            CorrelationSummaryItem(
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
            for c in top_correlations
        ]
        
        # Generate correlation insights
        correlation_insights = []
        for c in top_correlations[:3]:
            if c.causal_direction and c.causal_direction.value != 'none':
                correlation_insights.append(f"{c.metric_a.replace('_', ' ').title()} predicts {c.metric_b.replace('_', ' ')}")
            elif c.lag_days > 0:
                correlation_insights.append(f"{c.metric_a.replace('_', ' ').title()} affects {c.metric_b.replace('_', ' ')} after {c.lag_days} day(s)")
            elif abs(c.correlation_value) > 0.5:
                direction = "positively" if c.correlation_value > 0 else "negatively"
                correlation_insights.append(f"{c.metric_a.replace('_', ' ').title()} and {c.metric_b.replace('_', ' ')} are {direction} correlated")
        
        return DashboardResponse(
            user_id=str(user_id),
            period_start=start_date,
            period_end=end_date,
            daily_summaries=daily_summaries,
            total_anomalies=total_anomalies,
            unacknowledged_anomalies=unacknowledged,
            top_correlations=correlation_summaries,
            correlation_insights=correlation_insights,
        )
    
    async def _get_food_entries(self, user_id: uuid.UUID, start: date, end: date) -> List[FoodEntry]:
        result = await self.db.execute(
            select(FoodEntry).where(
                and_(
                    FoodEntry.user_id == user_id,
                    FoodEntry.date >= start,
                    FoodEntry.date <= end,
                )
            ).order_by(FoodEntry.date, FoodEntry.created_at)
        )
        return result.scalars().all()
    
    async def _get_sleep_entries(self, user_id: uuid.UUID, start: date, end: date) -> List[SleepEntry]:
        result = await self.db.execute(
            select(SleepEntry).where(
                and_(
                    SleepEntry.user_id == user_id,
                    SleepEntry.date >= start,
                    SleepEntry.date <= end,
                )
            ).order_by(SleepEntry.date)
        )
        return result.scalars().all()
    
    async def _get_exercise_entries(self, user_id: uuid.UUID, start: date, end: date) -> List[ExerciseEntry]:
        result = await self.db.execute(
            select(ExerciseEntry).where(
                and_(
                    ExerciseEntry.user_id == user_id,
                    ExerciseEntry.date >= start,
                    ExerciseEntry.date <= end,
                )
            ).order_by(ExerciseEntry.date, ExerciseEntry.created_at)
        )
        return result.scalars().all()
    
    async def _get_vital_signs(self, user_id: uuid.UUID, start: date, end: date) -> List[VitalSigns]:
        result = await self.db.execute(
            select(VitalSigns).where(
                and_(
                    VitalSigns.user_id == user_id,
                    VitalSigns.date >= start,
                    VitalSigns.date <= end,
                )
            ).order_by(VitalSigns.date, VitalSigns.created_at)
        )
        return result.scalars().all()
    
    async def _get_body_metrics(self, user_id: uuid.UUID, start: date, end: date) -> List[BodyMetrics]:
        result = await self.db.execute(
            select(BodyMetrics).where(
                and_(
                    BodyMetrics.user_id == user_id,
                    BodyMetrics.date >= start,
                    BodyMetrics.date <= end,
                )
            ).order_by(BodyMetrics.date)
        )
        return result.scalars().all()
    
    async def _get_chronic_metrics(self, user_id: uuid.UUID, start: date, end: date) -> List[ChronicMetrics]:
        result = await self.db.execute(
            select(ChronicMetrics).where(
                and_(
                    ChronicMetrics.user_id == user_id,
                    ChronicMetrics.date >= start,
                    ChronicMetrics.date <= end,
                )
            ).order_by(ChronicMetrics.date, ChronicMetrics.created_at)
        )
        return result.scalars().all()
    
    async def _get_anomalies(self, user_id: uuid.UUID, start: date, end: date) -> List[Anomaly]:
        result = await self.db.execute(
            select(Anomaly).where(
                and_(
                    Anomaly.user_id == user_id,
                    Anomaly.date >= start,
                    Anomaly.date <= end,
                )
            ).order_by(Anomaly.date, Anomaly.detected_at.desc())
        )
        return result.scalars().all()
    
    async def _get_top_correlations(self, user_id: uuid.UUID, limit: int = 5) -> List[Correlation]:
        """Get top actionable correlations for dashboard display."""
        # First try to get actionable correlations
        result = await self.db.execute(
            select(Correlation).where(
                and_(
                    Correlation.user_id == user_id,
                    Correlation.is_actionable == True,
                )
            ).order_by(Correlation.confidence_score.desc()).limit(limit)
        )
        correlations = result.scalars().all()
        
        # If not enough actionable, get any top correlations
        if len(correlations) < limit:
            result = await self.db.execute(
                select(Correlation).where(
                    Correlation.user_id == user_id
                ).order_by(Correlation.confidence_score.desc()).limit(limit)
            )
            correlations = result.scalars().all()
        
        return correlations