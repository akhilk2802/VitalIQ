"""
Recovery Readiness Predictor

Predicts a user's recovery readiness score (1-10) based on:
- Previous night's sleep (quality, duration, deep sleep %)
- Recent exercise load (past 3 days)
- HRV trend
- Resting heart rate deviation from baseline
"""

from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from datetime import date, timedelta
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import uuid

from app.models.sleep_entry import SleepEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns


@dataclass
class RecoveryPrediction:
    """Recovery readiness prediction result"""
    score: int  # 1-10 scale
    status: str  # ready_for_intense, ready_for_moderate, needs_rest, recovery_day
    message: str
    factors: Dict[str, float]  # Contribution of each factor
    recommendations: List[str]
    confidence: float  # 0-1 confidence in prediction
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovery_score": self.score,
            "status": self.status,
            "message": self.message,
            "factors": self.factors,
            "recommendations": self.recommendations,
            "confidence": round(self.confidence, 2)
        }


class RecoveryPredictor:
    """Predicts recovery readiness based on health metrics"""
    
    # Weights for each factor in the recovery score
    WEIGHTS = {
        "sleep_quality": 0.25,
        "sleep_duration": 0.20,
        "deep_sleep": 0.10,
        "hrv": 0.20,
        "resting_hr": 0.15,
        "exercise_load": 0.10,
    }
    
    # Status thresholds
    STATUS_THRESHOLDS = {
        "ready_for_intense": 8,
        "ready_for_moderate": 6,
        "needs_rest": 4,
        "recovery_day": 0,
    }
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self._baselines: Optional[Dict[str, float]] = None
    
    async def predict(self, target_date: Optional[date] = None) -> RecoveryPrediction:
        """
        Predict recovery readiness for a given date.
        
        Args:
            target_date: Date to predict for (defaults to today)
        
        Returns:
            RecoveryPrediction with score and recommendations
        """
        target_date = target_date or date.today()
        
        # Get baselines if not cached
        if self._baselines is None:
            self._baselines = await self._calculate_baselines()
        
        # Get relevant data
        sleep_data = await self._get_sleep_data(target_date)
        hrv_data = await self._get_hrv_data(target_date)
        exercise_load = await self._get_exercise_load(target_date)
        
        # Calculate factor scores (0-10 scale)
        factors = {}
        
        # Sleep quality contribution
        if sleep_data and sleep_data.get("quality_score"):
            quality_score = sleep_data["quality_score"]
            factors["sleep_quality"] = self._normalize_score(
                quality_score, 
                optimal_range=(70, 90),
                min_val=20, 
                max_val=100
            )
        else:
            factors["sleep_quality"] = 5.0  # Neutral if no data
        
        # Sleep duration contribution
        if sleep_data and sleep_data.get("duration_hours"):
            duration = sleep_data["duration_hours"]
            # Optimal is 7-9 hours
            if 7 <= duration <= 9:
                factors["sleep_duration"] = 10.0
            elif 6 <= duration < 7 or 9 < duration <= 10:
                factors["sleep_duration"] = 7.0
            elif 5 <= duration < 6:
                factors["sleep_duration"] = 4.0
            else:
                factors["sleep_duration"] = 2.0
        else:
            factors["sleep_duration"] = 5.0
        
        # Deep sleep contribution
        if sleep_data and sleep_data.get("deep_sleep_pct"):
            deep_pct = sleep_data["deep_sleep_pct"]
            # Optimal deep sleep is 15-25%
            factors["deep_sleep"] = self._normalize_score(
                deep_pct,
                optimal_range=(15, 25),
                min_val=5,
                max_val=35
            )
        else:
            factors["deep_sleep"] = 5.0
        
        # HRV contribution (higher is better for recovery)
        if hrv_data and hrv_data.get("hrv_ms") is not None:
            hrv = hrv_data["hrv_ms"]
            baseline_hrv = self._baselines.get("hrv_ms", 45)
            hrv_deviation = (hrv - baseline_hrv) / baseline_hrv if baseline_hrv > 0 else 0
            # +20% above baseline = 10, -20% below = 2
            factors["hrv"] = max(2, min(10, 6 + hrv_deviation * 20))
        else:
            factors["hrv"] = 5.0
        
        # Resting HR contribution (lower is better)
        if hrv_data and hrv_data.get("resting_hr") is not None:
            rhr = hrv_data["resting_hr"]
            baseline_rhr = self._baselines.get("resting_hr", 65)
            rhr_deviation = (rhr - baseline_rhr) / baseline_rhr if baseline_rhr > 0 else 0
            # Lower than baseline = good, higher = bad
            factors["resting_hr"] = max(2, min(10, 6 - rhr_deviation * 30))
        else:
            factors["resting_hr"] = 5.0
        
        # Exercise load contribution (recent heavy exercise = need more recovery)
        if exercise_load:
            load_score = exercise_load.get("load_score", 0)
            # High load in past 3 days = lower recovery score
            factors["exercise_load"] = max(2, 10 - load_score * 2)
        else:
            factors["exercise_load"] = 7.0  # No recent exercise = rested
        
        # Calculate weighted score
        total_score = sum(
            factors[factor] * weight 
            for factor, weight in self.WEIGHTS.items()
        )
        
        # Round to integer 1-10
        final_score = max(1, min(10, round(total_score)))
        
        # Determine status
        status = self._get_status(final_score)
        message = self._get_message(final_score, factors)
        recommendations = self._get_recommendations(final_score, factors)
        
        # Calculate confidence based on data availability
        data_points = sum([
            1 if sleep_data else 0,
            1 if hrv_data else 0,
            1 if exercise_load else 0,
        ])
        confidence = data_points / 3
        
        return RecoveryPrediction(
            score=final_score,
            status=status,
            message=message,
            factors={k: round(v, 1) for k, v in factors.items()},
            recommendations=recommendations,
            confidence=confidence
        )
    
    async def _calculate_baselines(self, days: int = 30) -> Dict[str, float]:
        """Calculate baseline values from historical data"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        baselines = {}
        
        # HRV baseline
        hrv_result = await self.db.execute(
            select(func.avg(VitalSigns.hrv_ms))
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= start_date,
                VitalSigns.date <= end_date,
                VitalSigns.hrv_ms.isnot(None)
            ))
        )
        baselines["hrv_ms"] = hrv_result.scalar() or 45
        
        # Resting HR baseline
        rhr_result = await self.db.execute(
            select(func.avg(VitalSigns.resting_heart_rate))
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= start_date,
                VitalSigns.date <= end_date,
                VitalSigns.resting_heart_rate.isnot(None)
            ))
        )
        baselines["resting_hr"] = rhr_result.scalar() or 65
        
        # Sleep duration baseline
        sleep_result = await self.db.execute(
            select(func.avg(SleepEntry.duration_hours))
            .where(and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date >= start_date,
                SleepEntry.date <= end_date
            ))
        )
        baselines["sleep_hours"] = sleep_result.scalar() or 7
        
        return baselines
    
    async def _get_sleep_data(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get sleep data from the night before target date"""
        result = await self.db.execute(
            select(SleepEntry)
            .where(and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date == target_date
            ))
        )
        sleep = result.scalar_one_or_none()
        
        if not sleep:
            return None
        
        deep_sleep_pct = None
        if sleep.duration_hours and sleep.duration_hours > 0 and sleep.deep_sleep_minutes:
            deep_sleep_pct = (sleep.deep_sleep_minutes / (sleep.duration_hours * 60)) * 100
        
        return {
            "quality_score": sleep.quality_score,
            "duration_hours": sleep.duration_hours,
            "deep_sleep_minutes": sleep.deep_sleep_minutes,
            "deep_sleep_pct": deep_sleep_pct,
            "awakenings": sleep.awakenings,
        }
    
    async def _get_hrv_data(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get HRV and resting HR from morning vitals"""
        result = await self.db.execute(
            select(VitalSigns)
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date == target_date
            ))
        )
        vitals = result.scalar_one_or_none()
        
        if not vitals:
            return None
        
        return {
            "hrv_ms": vitals.hrv_ms,
            "resting_hr": vitals.resting_heart_rate,
        }
    
    async def _get_exercise_load(self, target_date: date, lookback_days: int = 3) -> Optional[Dict[str, Any]]:
        """Calculate exercise load from past few days"""
        start_date = target_date - timedelta(days=lookback_days)
        
        result = await self.db.execute(
            select(ExerciseEntry)
            .where(and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= start_date,
                ExerciseEntry.date < target_date
            ))
        )
        exercises = result.scalars().all()
        
        if not exercises:
            return None
        
        # Calculate load score based on duration and intensity
        total_minutes = 0
        intensity_weighted_minutes = 0
        
        for ex in exercises:
            duration = ex.duration_minutes or 0
            total_minutes += duration
            
            # Weight by intensity
            intensity_multiplier = {
                "low": 0.5,
                "moderate": 1.0,
                "high": 1.5,
            }.get(ex.intensity.value if ex.intensity else "moderate", 1.0)
            
            intensity_weighted_minutes += duration * intensity_multiplier
        
        # Normalize to 0-5 scale (300+ weighted minutes in 3 days = high load)
        load_score = min(5, intensity_weighted_minutes / 60)
        
        return {
            "total_minutes": total_minutes,
            "intensity_weighted_minutes": intensity_weighted_minutes,
            "load_score": load_score,
            "exercise_count": len(exercises),
        }
    
    def _normalize_score(
        self, 
        value: float, 
        optimal_range: tuple, 
        min_val: float, 
        max_val: float
    ) -> float:
        """Normalize a value to 0-10 scale with optimal range"""
        opt_min, opt_max = optimal_range
        
        if opt_min <= value <= opt_max:
            return 10.0
        elif value < opt_min:
            # Scale from min_val to optimal
            range_size = opt_min - min_val
            if range_size <= 0:
                return 5.0
            return max(0, 10 * (value - min_val) / range_size)
        else:
            # Scale from optimal to max_val
            range_size = max_val - opt_max
            if range_size <= 0:
                return 5.0
            return max(0, 10 * (max_val - value) / range_size)
    
    def _get_status(self, score: int) -> str:
        """Get status string from score"""
        if score >= self.STATUS_THRESHOLDS["ready_for_intense"]:
            return "ready_for_intense"
        elif score >= self.STATUS_THRESHOLDS["ready_for_moderate"]:
            return "ready_for_moderate"
        elif score >= self.STATUS_THRESHOLDS["needs_rest"]:
            return "needs_rest"
        else:
            return "recovery_day"
    
    def _get_message(self, score: int, factors: Dict[str, float]) -> str:
        """Generate human-readable message based on score and factors"""
        if score >= 8:
            return "Your body is well-recovered. Great day for an intense workout!"
        elif score >= 6:
            return "Good recovery. You're ready for moderate activity today."
        elif score >= 4:
            # Identify main limiting factor
            min_factor = min(factors, key=factors.get)
            factor_messages = {
                "sleep_quality": "Your sleep quality was below average.",
                "sleep_duration": "You didn't get enough sleep.",
                "deep_sleep": "Your deep sleep was insufficient.",
                "hrv": "Your HRV indicates some stress on your system.",
                "resting_hr": "Your resting heart rate is elevated.",
                "exercise_load": "Recent exercise load is still in your system.",
            }
            return f"Consider lighter activity today. {factor_messages.get(min_factor, '')}"
        else:
            return "Your body needs rest today. Focus on recovery activities."
    
    def _get_recommendations(self, score: int, factors: Dict[str, float]) -> List[str]:
        """Generate recommendations based on score and factors"""
        recommendations = []
        
        if score >= 8:
            recommendations.append("Perfect for HIIT, heavy lifting, or long runs")
            recommendations.append("Consider pushing your limits today")
        elif score >= 6:
            recommendations.append("Good for 30-45 min moderate workout")
            recommendations.append("Mix cardio with light strength training")
        elif score >= 4:
            recommendations.append("Light activity like walking or yoga")
            recommendations.append("Focus on mobility and stretching")
        else:
            recommendations.append("Rest day - active recovery only")
            recommendations.append("Try meditation or gentle stretching")
        
        # Factor-specific recommendations
        if factors.get("sleep_quality", 10) < 5:
            recommendations.append("Improve sleep: limit screens before bed")
        
        if factors.get("sleep_duration", 10) < 5:
            recommendations.append("Aim for 7-9 hours of sleep tonight")
        
        if factors.get("hrv", 10) < 5:
            recommendations.append("Practice deep breathing to improve HRV")
        
        if factors.get("resting_hr", 10) < 5:
            recommendations.append("Stay hydrated and manage stress")
        
        return recommendations[:4]  # Limit to 4 recommendations
