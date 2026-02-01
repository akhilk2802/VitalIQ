"""
Food Cravings Predictor

Predicts food cravings with reasoning and countermeasures based on:
- Sleep quality and duration
- Stress level (HRV)
- Recent sugar/carb intake
- Activity level
- Time patterns
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import date, timedelta, time
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.sleep_entry import SleepEntry
from app.models.vital_signs import VitalSigns
from app.models.food_entry import FoodEntry
from app.models.exercise_entry import ExerciseEntry


@dataclass
class CravingPrediction:
    """Food craving prediction result"""
    craving_type: str  # sugar, carbs, salty, comfort_food, none
    likelihood: float  # 0-1 probability
    intensity: str  # low, moderate, high
    reasoning: str  # Human-readable explanation
    countermeasures: List[str]  # Actionable recommendations
    peak_time: Optional[str]  # When craving is likely to peak
    trigger_factors: Dict[str, float]  # Contribution of each factor
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "craving_type": self.craving_type,
            "likelihood": round(self.likelihood, 2),
            "intensity": self.intensity,
            "reasoning": self.reasoning,
            "countermeasures": self.countermeasures,
            "peak_time": self.peak_time,
            "trigger_factors": {k: round(v, 2) for k, v in self.trigger_factors.items()}
        }


@dataclass
class DailyCravingsForecast:
    """Full day's craving forecast"""
    date: date
    primary_craving: CravingPrediction
    secondary_cravings: List[CravingPrediction]
    overall_risk: str  # low, moderate, high
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "primary_craving": self.primary_craving.to_dict(),
            "secondary_cravings": [c.to_dict() for c in self.secondary_cravings],
            "overall_risk": self.overall_risk,
            "summary": self.summary
        }


class CravingsPredictor:
    """Predicts food cravings based on health patterns"""
    
    # Craving type configurations
    CRAVING_TYPES = {
        "sugar": {
            "triggers": ["low_sleep", "low_hrv", "low_activity", "carb_cycle"],
            "peak_times": ["2-4 PM", "8-10 PM"],
            "countermeasures": [
                "Have protein-rich breakfast within 1hr of waking",
                "Prepare healthy snacks: nuts, Greek yogurt, berries",
                "Avoid skipping meals - eat every 3-4 hours",
                "Stay hydrated - thirst can feel like sugar craving",
                "Take a 10-min walk when craving hits",
            ]
        },
        "carbs": {
            "triggers": ["high_activity", "low_sleep", "stress"],
            "peak_times": ["12-2 PM", "6-8 PM"],
            "countermeasures": [
                "Include complex carbs with each meal",
                "Pair carbs with protein to stabilize blood sugar",
                "Plan satisfying meals to prevent evening snacking",
                "Consider oatmeal or whole grain toast for breakfast",
            ]
        },
        "salty": {
            "triggers": ["dehydration", "high_activity", "stress"],
            "peak_times": ["3-5 PM"],
            "countermeasures": [
                "Increase water intake throughout the day",
                "Add electrolytes if exercising heavily",
                "Choose healthier salty options: pickles, olives",
                "Check if you're actually hungry vs. dehydrated",
            ]
        },
        "comfort_food": {
            "triggers": ["stress", "low_sleep", "low_hrv"],
            "peak_times": ["7-9 PM"],
            "countermeasures": [
                "Practice stress management: deep breathing, meditation",
                "Plan a satisfying dinner that feels indulgent but healthy",
                "Address emotional needs directly - journal, talk, rest",
                "Keep comfort foods out of the house if struggling",
            ]
        }
    }
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self._baselines: Optional[Dict[str, float]] = None
    
    async def predict(self, target_date: Optional[date] = None) -> DailyCravingsForecast:
        """
        Predict food cravings for a given date.
        
        Args:
            target_date: Date to predict for (defaults to today)
        
        Returns:
            DailyCravingsForecast with predictions and countermeasures
        """
        target_date = target_date or date.today()
        
        # Get baselines
        if self._baselines is None:
            self._baselines = await self._calculate_baselines()
        
        # Gather relevant data
        sleep_data = await self._get_previous_sleep(target_date)
        hrv_data = await self._get_recent_hrv(target_date)
        nutrition_data = await self._get_recent_nutrition(target_date)
        activity_data = await self._get_recent_activity(target_date)
        
        # Calculate trigger factors
        triggers = self._calculate_triggers(
            sleep_data, hrv_data, nutrition_data, activity_data
        )
        
        # Predict each craving type
        predictions = []
        for craving_type in self.CRAVING_TYPES:
            prediction = self._predict_craving_type(
                craving_type, triggers, sleep_data, nutrition_data
            )
            if prediction.likelihood > 0.2:  # Only include if somewhat likely
                predictions.append(prediction)
        
        # Sort by likelihood
        predictions.sort(key=lambda p: p.likelihood, reverse=True)
        
        # Get primary and secondary cravings
        if predictions:
            primary = predictions[0]
            secondary = predictions[1:3]  # Top 2 secondary
        else:
            # No significant cravings predicted
            primary = CravingPrediction(
                craving_type="none",
                likelihood=0.1,
                intensity="low",
                reasoning="Your patterns suggest stable energy today",
                countermeasures=["Maintain regular meal timing", "Stay hydrated"],
                peak_time=None,
                trigger_factors=triggers
            )
            secondary = []
        
        # Determine overall risk
        if primary.likelihood > 0.7:
            overall_risk = "high"
        elif primary.likelihood > 0.4:
            overall_risk = "moderate"
        else:
            overall_risk = "low"
        
        # Generate summary
        summary = self._generate_summary(primary, triggers, sleep_data)
        
        return DailyCravingsForecast(
            date=target_date,
            primary_craving=primary,
            secondary_cravings=secondary,
            overall_risk=overall_risk,
            summary=summary
        )
    
    async def _calculate_baselines(self, days: int = 30) -> Dict[str, float]:
        """Calculate baseline values"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        baselines = {}
        
        # Sleep baseline
        sleep_result = await self.db.execute(
            select(func.avg(SleepEntry.duration_hours))
            .where(and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date >= start_date
            ))
        )
        baselines["sleep_hours"] = sleep_result.scalar() or 7
        
        # HRV baseline
        hrv_result = await self.db.execute(
            select(func.avg(VitalSigns.hrv_ms))
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= start_date,
                VitalSigns.hrv_ms.isnot(None)
            ))
        )
        baselines["hrv_ms"] = hrv_result.scalar() or 45
        
        # Daily sugar baseline
        sugar_result = await self.db.execute(
            select(func.avg(FoodEntry.sugar_g))
            .where(and_(
                FoodEntry.user_id == self.user_id,
                FoodEntry.date >= start_date
            ))
        )
        baselines["daily_sugar"] = (sugar_result.scalar() or 50) * 3  # Approximate daily
        
        # Exercise minutes baseline
        exercise_result = await self.db.execute(
            select(func.avg(ExerciseEntry.duration_minutes))
            .where(and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= start_date
            ))
        )
        baselines["exercise_minutes"] = exercise_result.scalar() or 30
        
        return baselines
    
    async def _get_previous_sleep(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get sleep data from night before"""
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
        
        return {
            "duration_hours": sleep.duration_hours,
            "quality_score": sleep.quality_score,
            "awakenings": sleep.awakenings,
        }
    
    async def _get_recent_hrv(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get recent HRV data"""
        # Get today's or most recent HRV
        result = await self.db.execute(
            select(VitalSigns)
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date <= target_date
            ))
            .order_by(VitalSigns.date.desc())
            .limit(1)
        )
        vitals = result.scalar_one_or_none()
        
        if not vitals:
            return None
        
        return {
            "hrv_ms": vitals.hrv_ms,
            "date": vitals.date,
        }
    
    async def _get_recent_nutrition(self, target_date: date, days: int = 3) -> Dict[str, Any]:
        """Get recent nutrition patterns"""
        start_date = target_date - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                func.sum(FoodEntry.sugar_g).label("total_sugar"),
                func.sum(FoodEntry.carbs_g).label("total_carbs"),
                func.sum(FoodEntry.protein_g).label("total_protein"),
                func.count(FoodEntry.id).label("meal_count")
            )
            .where(and_(
                FoodEntry.user_id == self.user_id,
                FoodEntry.date >= start_date,
                FoodEntry.date < target_date
            ))
        )
        row = result.one()
        
        return {
            "avg_daily_sugar": (row.total_sugar or 0) / days,
            "avg_daily_carbs": (row.total_carbs or 0) / days,
            "avg_daily_protein": (row.total_protein or 0) / days,
            "meals_per_day": (row.meal_count or 0) / days,
        }
    
    async def _get_recent_activity(self, target_date: date, days: int = 3) -> Dict[str, Any]:
        """Get recent activity levels"""
        start_date = target_date - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                func.sum(ExerciseEntry.duration_minutes).label("total_minutes"),
                func.sum(ExerciseEntry.calories_burned).label("total_calories"),
                func.count(ExerciseEntry.id).label("workout_count")
            )
            .where(and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= start_date,
                ExerciseEntry.date < target_date
            ))
        )
        row = result.one()
        
        return {
            "avg_daily_minutes": (row.total_minutes or 0) / days,
            "total_workouts": row.workout_count or 0,
            "avg_daily_calories": (row.total_calories or 0) / days,
        }
    
    def _calculate_triggers(
        self,
        sleep_data: Optional[Dict],
        hrv_data: Optional[Dict],
        nutrition_data: Dict,
        activity_data: Dict
    ) -> Dict[str, float]:
        """Calculate trigger factors (0-1 scale)"""
        triggers = {}
        
        # Low sleep trigger
        if sleep_data:
            sleep_hours = sleep_data.get("duration_hours", 7)
            baseline_sleep = self._baselines.get("sleep_hours", 7)
            if sleep_hours < 6:
                triggers["low_sleep"] = min(1.0, (6 - sleep_hours) / 3)
            elif sleep_hours < baseline_sleep - 1:
                triggers["low_sleep"] = 0.4
            else:
                triggers["low_sleep"] = 0.1
        else:
            triggers["low_sleep"] = 0.3  # Unknown = moderate risk
        
        # Low HRV (stress) trigger
        if hrv_data and hrv_data.get("hrv_ms"):
            hrv = hrv_data["hrv_ms"]
            baseline_hrv = self._baselines.get("hrv_ms", 45)
            if hrv < baseline_hrv * 0.8:
                triggers["low_hrv"] = min(1.0, (baseline_hrv - hrv) / baseline_hrv)
            else:
                triggers["low_hrv"] = 0.1
        else:
            triggers["low_hrv"] = 0.2
        
        # Stress indicator (combination)
        triggers["stress"] = (triggers["low_sleep"] + triggers["low_hrv"]) / 2
        
        # Low activity trigger
        avg_activity = activity_data.get("avg_daily_minutes", 0)
        baseline_activity = self._baselines.get("exercise_minutes", 30)
        if avg_activity < 15:
            triggers["low_activity"] = 0.7
        elif avg_activity < baseline_activity * 0.5:
            triggers["low_activity"] = 0.4
        else:
            triggers["low_activity"] = 0.1
        
        # High activity trigger (for carb cravings)
        if avg_activity > baseline_activity * 1.5:
            triggers["high_activity"] = min(1.0, avg_activity / (baseline_activity * 2))
        else:
            triggers["high_activity"] = 0.1
        
        # Carb cycle trigger (recent low carbs)
        avg_carbs = nutrition_data.get("avg_daily_carbs", 150)
        if avg_carbs < 100:
            triggers["carb_cycle"] = min(1.0, (100 - avg_carbs) / 100)
        else:
            triggers["carb_cycle"] = 0.1
        
        # Dehydration proxy (high activity + low meals)
        meals_per_day = nutrition_data.get("meals_per_day", 3)
        if meals_per_day < 2.5 and avg_activity > 30:
            triggers["dehydration"] = 0.5
        else:
            triggers["dehydration"] = 0.1
        
        return triggers
    
    def _predict_craving_type(
        self,
        craving_type: str,
        triggers: Dict[str, float],
        sleep_data: Optional[Dict],
        nutrition_data: Dict
    ) -> CravingPrediction:
        """Predict likelihood and details for a specific craving type"""
        config = self.CRAVING_TYPES[craving_type]
        
        # Calculate likelihood from relevant triggers
        relevant_triggers = config["triggers"]
        trigger_values = [triggers.get(t, 0) for t in relevant_triggers]
        
        if trigger_values:
            # Weighted average with max contributing more
            base_likelihood = sum(trigger_values) / len(trigger_values)
            max_trigger = max(trigger_values)
            likelihood = 0.6 * base_likelihood + 0.4 * max_trigger
        else:
            likelihood = 0.1
        
        # Adjust for specific patterns
        if craving_type == "sugar" and sleep_data:
            if sleep_data.get("duration_hours", 7) < 5:
                likelihood = min(1.0, likelihood + 0.3)
        
        # Determine intensity
        if likelihood > 0.7:
            intensity = "high"
        elif likelihood > 0.4:
            intensity = "moderate"
        else:
            intensity = "low"
        
        # Generate reasoning
        reasoning = self._generate_reasoning(craving_type, triggers, sleep_data)
        
        # Select countermeasures
        countermeasures = config["countermeasures"][:4]  # Top 4
        
        # Determine peak time
        peak_time = config["peak_times"][0] if config["peak_times"] else None
        
        return CravingPrediction(
            craving_type=craving_type,
            likelihood=likelihood,
            intensity=intensity,
            reasoning=reasoning,
            countermeasures=countermeasures,
            peak_time=peak_time,
            trigger_factors={t: triggers.get(t, 0) for t in relevant_triggers}
        )
    
    def _generate_reasoning(
        self,
        craving_type: str,
        triggers: Dict[str, float],
        sleep_data: Optional[Dict]
    ) -> str:
        """Generate human-readable reasoning for prediction"""
        reasons = []
        
        if triggers.get("low_sleep", 0) > 0.3:
            if sleep_data:
                hours = sleep_data.get("duration_hours", "insufficient")
                reasons.append(f"{hours:.1f}hr sleep last night")
            else:
                reasons.append("sleep data suggests fatigue")
        
        if triggers.get("low_hrv", 0) > 0.3:
            reasons.append("elevated stress markers")
        
        if triggers.get("low_activity", 0) > 0.3:
            reasons.append("lower than usual activity")
        
        if triggers.get("high_activity", 0) > 0.3:
            reasons.append("high recent exercise")
        
        if triggers.get("carb_cycle", 0) > 0.3:
            reasons.append("low recent carb intake")
        
        if not reasons:
            return f"Mild {craving_type} craving based on general patterns"
        
        reason_str = " + ".join(reasons)
        
        explanations = {
            "sugar": f"Based on {reason_str}, your body will likely seek quick energy through sugar",
            "carbs": f"With {reason_str}, you may crave carbohydrates for energy restoration",
            "salty": f"Given {reason_str}, salty food cravings are possible",
            "comfort_food": f"Due to {reason_str}, comfort food may be appealing"
        }
        
        return explanations.get(craving_type, f"Based on {reason_str}")
    
    def _generate_summary(
        self,
        primary: CravingPrediction,
        triggers: Dict[str, float],
        sleep_data: Optional[Dict]
    ) -> str:
        """Generate overall summary"""
        if primary.craving_type == "none":
            return "Your patterns suggest stable energy and minimal craving risk today."
        
        intensity_word = {
            "low": "mild",
            "moderate": "moderate", 
            "high": "strong"
        }.get(primary.intensity, "some")
        
        time_hint = f" (likely around {primary.peak_time})" if primary.peak_time else ""
        
        return (
            f"Expect {intensity_word} {primary.craving_type} cravings today{time_hint}. "
            f"{primary.countermeasures[0] if primary.countermeasures else 'Stay prepared.'}"
        )
