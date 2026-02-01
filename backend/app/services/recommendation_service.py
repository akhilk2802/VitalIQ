"""
Hybrid Recommendation Service

Combines rule-based and AI-powered recommendations based on:
- Detected correlations
- Anomaly patterns
- Health metrics trends
- Recovery and craving predictions
"""

from typing import List, Dict, Optional, Any
from datetime import date, timedelta
from dataclasses import dataclass
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import uuid

from openai import AsyncOpenAI

from app.config import settings
from app.models.correlation import Correlation
from app.models.anomaly import Anomaly
from app.models.sleep_entry import SleepEntry
from app.models.food_entry import FoodEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.ml.prediction.recovery import RecoveryPredictor
from app.ml.prediction.cravings import CravingsPredictor


@dataclass
class Recommendation:
    """A single recommendation"""
    id: str
    category: str  # exercise, nutrition, sleep, wellness, medical
    priority: str  # high, medium, low
    title: str
    message: str
    reasoning: str
    source: str  # rule, correlation, ai
    confidence: float
    actions: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "message": self.message,
            "reasoning": self.reasoning,
            "source": self.source,
            "confidence": round(self.confidence, 2),
            "actions": self.actions
        }


class RecommendationService:
    """Hybrid recommendation engine combining rules and AI"""
    
    # Rule-based recommendation triggers
    RULES = {
        "low_sleep_sugar_risk": {
            "condition": lambda ctx: ctx.get("sleep_hours", 8) < 6,
            "category": "nutrition",
            "priority": "high",
            "title": "Prepare for Sugar Cravings",
            "message": "Your sleep was under 6 hours. This typically triggers sugar cravings.",
            "actions": [
                "Have protein-rich breakfast within 1hr of waking",
                "Prepare healthy snacks: nuts, cheese, Greek yogurt",
                "Stay hydrated throughout the day"
            ]
        },
        "exercise_improves_sleep": {
            "condition": lambda ctx: ctx.get("sleep_quality", 100) < 60 and ctx.get("exercise_today", False) is False,
            "category": "exercise",
            "priority": "medium",
            "title": "Exercise for Better Sleep",
            "message": "Your sleep quality has been low. 30 min exercise can improve tonight's sleep.",
            "actions": [
                "Aim for 30-45 min moderate activity",
                "Best time: morning or early afternoon",
                "Avoid intense exercise within 3hrs of bedtime"
            ]
        },
        "high_hr_rest_needed": {
            "condition": lambda ctx: ctx.get("resting_hr_deviation", 0) > 10,
            "category": "wellness",
            "priority": "high",
            "title": "Elevated Heart Rate",
            "message": "Your resting heart rate is higher than usual. Consider rest and stress management.",
            "actions": [
                "Practice deep breathing exercises",
                "Reduce caffeine intake today",
                "Consider a lighter workout or rest day"
            ]
        },
        "low_hrv_stress": {
            "condition": lambda ctx: ctx.get("hrv_deviation", 0) < -10,
            "category": "wellness",
            "priority": "medium",
            "title": "Stress Indicators Elevated",
            "message": "Your HRV suggests elevated stress. Focus on recovery activities.",
            "actions": [
                "10-15 min meditation or breathing exercises",
                "Take short breaks throughout the day",
                "Prioritize 7-8 hours sleep tonight"
            ]
        },
        "consistent_exercise_streak": {
            "condition": lambda ctx: ctx.get("exercise_streak", 0) >= 5,
            "category": "exercise",
            "priority": "low",
            "title": "Great Exercise Streak!",
            "message": f"You've exercised consistently. Consider a recovery day soon.",
            "actions": [
                "Plan a rest or active recovery day",
                "Focus on mobility and stretching",
                "Celebrate your consistency!"
            ]
        },
        "protein_deficit": {
            "condition": lambda ctx: ctx.get("avg_protein_ratio", 0.2) < 0.15,
            "category": "nutrition",
            "priority": "medium",
            "title": "Increase Protein Intake",
            "message": "Your protein intake has been below optimal. Protein supports recovery and satiety.",
            "actions": [
                "Add protein to each meal (eggs, chicken, fish, legumes)",
                "Consider protein-rich snacks",
                "Aim for 0.8-1g protein per kg body weight"
            ]
        },
        "sugar_spike_pattern": {
            "condition": lambda ctx: ctx.get("sugar_anomalies", 0) >= 2,
            "category": "nutrition",
            "priority": "high",
            "title": "Sugar Intake Pattern",
            "message": "You've had multiple high-sugar days. Consider moderating intake.",
            "actions": [
                "Replace sugary snacks with fruits or nuts",
                "Check labels for hidden sugars",
                "Pair carbs with protein to stabilize blood sugar"
            ]
        },
        "sleep_consistency": {
            "condition": lambda ctx: ctx.get("sleep_time_variance", 0) > 90,
            "category": "sleep",
            "priority": "medium",
            "title": "Improve Sleep Consistency",
            "message": "Your bedtime varies significantly. Consistent sleep times improve quality.",
            "actions": [
                "Set a target bedtime and wake time",
                "Start wind-down routine 30 min before bed",
                "Avoid screens 1hr before sleep"
            ]
        }
    }
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def get_recommendations(
        self,
        days: int = 7,
        include_ai: bool = True,
        max_recommendations: int = 8
    ) -> List[Recommendation]:
        """
        Get personalized recommendations based on recent health data.
        
        Args:
            days: Number of days to analyze
            include_ai: Whether to include AI-generated recommendations
            max_recommendations: Maximum number of recommendations to return
        
        Returns:
            List of prioritized recommendations
        """
        # Build context from recent data
        context = await self._build_context(days)
        
        # Get rule-based recommendations
        recommendations = self._evaluate_rules(context)
        
        # Get correlation-based recommendations
        correlation_recs = await self._get_correlation_recommendations()
        recommendations.extend(correlation_recs)
        
        # Get AI recommendations if enabled
        if include_ai and self.openai_client:
            ai_recs = await self._get_ai_recommendations(context)
            recommendations.extend(ai_recs)
        
        # Deduplicate and prioritize
        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations = self._prioritize_recommendations(recommendations)
        
        return recommendations[:max_recommendations]
    
    async def _build_context(self, days: int) -> Dict[str, Any]:
        """Build context from recent health data"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        context = {}
        
        # Get sleep data
        sleep_result = await self.db.execute(
            select(SleepEntry)
            .where(and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date >= start_date
            ))
            .order_by(SleepEntry.date.desc())
        )
        sleep_entries = sleep_result.scalars().all()
        
        if sleep_entries:
            context["sleep_hours"] = sleep_entries[0].duration_hours if sleep_entries else 7
            context["sleep_quality"] = sleep_entries[0].quality_score if sleep_entries else 70
            
            sleep_hours_list = [s.duration_hours for s in sleep_entries if s.duration_hours]
            context["avg_sleep_hours"] = sum(sleep_hours_list) / len(sleep_hours_list) if sleep_hours_list else 7
            
            # Calculate bedtime variance
            if len(sleep_entries) >= 3:
                import statistics
                bedtimes = [s.bedtime.hour * 60 + s.bedtime.minute for s in sleep_entries if s.bedtime]
                if bedtimes:
                    context["sleep_time_variance"] = statistics.stdev(bedtimes) if len(bedtimes) > 1 else 0
        
        # Get exercise data
        exercise_result = await self.db.execute(
            select(ExerciseEntry)
            .where(and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= start_date
            ))
            .order_by(ExerciseEntry.date.desc())
        )
        exercises = exercise_result.scalars().all()
        
        context["exercise_today"] = any(e.date == end_date for e in exercises)
        context["exercise_days"] = len(set(e.date for e in exercises))
        
        # Calculate exercise streak
        streak = 0
        check_date = end_date
        exercise_dates = set(e.date for e in exercises)
        while check_date in exercise_dates:
            streak += 1
            check_date -= timedelta(days=1)
        context["exercise_streak"] = streak
        
        # Get vitals data
        vitals_result = await self.db.execute(
            select(VitalSigns)
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= start_date
            ))
            .order_by(VitalSigns.date.desc())
        )
        vitals = vitals_result.scalars().all()
        
        if vitals:
            recent_hr = vitals[0].resting_heart_rate
            recent_hrv = vitals[0].hrv_ms
            
            # Calculate averages for baseline comparison
            hr_values = [v.resting_heart_rate for v in vitals if v.resting_heart_rate]
            hrv_values = [v.hrv_ms for v in vitals if v.hrv_ms]
            
            if hr_values:
                avg_hr = sum(hr_values) / len(hr_values)
                context["resting_hr_deviation"] = recent_hr - avg_hr if recent_hr else 0
            
            if hrv_values:
                avg_hrv = sum(hrv_values) / len(hrv_values)
                context["hrv_deviation"] = recent_hrv - avg_hrv if recent_hrv else 0
        
        # Get nutrition data
        food_result = await self.db.execute(
            select(FoodEntry)
            .where(and_(
                FoodEntry.user_id == self.user_id,
                FoodEntry.date >= start_date
            ))
        )
        foods = food_result.scalars().all()
        
        if foods:
            total_calories = sum(f.calories or 0 for f in foods)
            total_protein = sum(f.protein_g or 0 for f in foods)
            total_sugar = sum(f.sugar_g or 0 for f in foods)
            
            if total_calories > 0:
                context["avg_protein_ratio"] = (total_protein * 4) / total_calories
            
            # Count high sugar days
            from collections import defaultdict
            daily_sugar = defaultdict(float)
            for f in foods:
                daily_sugar[f.date] += f.sugar_g or 0
            
            high_sugar_days = sum(1 for s in daily_sugar.values() if s > 75)
            context["sugar_anomalies"] = high_sugar_days
        
        # Get anomaly count
        anomaly_result = await self.db.execute(
            select(func.count(Anomaly.id))
            .where(and_(
                Anomaly.user_id == self.user_id,
                Anomaly.date >= start_date
            ))
        )
        context["recent_anomalies"] = anomaly_result.scalar() or 0
        
        return context
    
    def _evaluate_rules(self, context: Dict[str, Any]) -> List[Recommendation]:
        """Evaluate rule-based recommendations"""
        recommendations = []
        
        for rule_id, rule in self.RULES.items():
            try:
                if rule["condition"](context):
                    recommendations.append(Recommendation(
                        id=rule_id,
                        category=rule["category"],
                        priority=rule["priority"],
                        title=rule["title"],
                        message=rule["message"],
                        reasoning="Based on your recent health patterns",
                        source="rule",
                        confidence=0.85,
                        actions=rule["actions"]
                    ))
            except Exception:
                continue  # Skip rules that fail due to missing context
        
        return recommendations
    
    async def _get_correlation_recommendations(self) -> List[Recommendation]:
        """Get recommendations based on detected correlations"""
        recommendations = []
        
        # Get actionable correlations
        result = await self.db.execute(
            select(Correlation)
            .where(and_(
                Correlation.user_id == self.user_id,
                Correlation.is_actionable == True
            ))
            .order_by(Correlation.confidence_score.desc())
            .limit(3)
        )
        correlations = result.scalars().all()
        
        for corr in correlations:
            if corr.recommendation:
                recommendations.append(Recommendation(
                    id=f"corr_{corr.id}",
                    category="wellness",
                    priority="medium",
                    title=f"{corr.metric_a.replace('_', ' ').title()} & {corr.metric_b.replace('_', ' ').title()}",
                    message=corr.insight or f"These metrics are strongly correlated in your data.",
                    reasoning=f"Based on {corr.strength.value} correlation detected over {corr.sample_size} days",
                    source="correlation",
                    confidence=corr.confidence_score or 0.7,
                    actions=[corr.recommendation]
                ))
        
        return recommendations
    
    async def _get_ai_recommendations(self, context: Dict[str, Any]) -> List[Recommendation]:
        """Get AI-generated personalized recommendations"""
        if not self.openai_client:
            return []
        
        prompt = f"""You are a health advisor analyzing user health data. Based on the context below, provide 2-3 specific, actionable recommendations.

Context:
- Recent sleep: {context.get('avg_sleep_hours', 'N/A')} hrs avg, quality {context.get('sleep_quality', 'N/A')}%
- Exercise: {context.get('exercise_days', 0)} days in past week, streak of {context.get('exercise_streak', 0)} days
- Heart rate deviation: {context.get('resting_hr_deviation', 0):.1f} bpm from baseline
- HRV deviation: {context.get('hrv_deviation', 0):.1f} ms from baseline
- Recent anomalies: {context.get('recent_anomalies', 0)}
- Sleep time variance: {context.get('sleep_time_variance', 0):.0f} minutes

Provide recommendations in this JSON format:
{{
    "recommendations": [
        {{
            "category": "exercise|nutrition|sleep|wellness",
            "priority": "high|medium|low",
            "title": "Short title",
            "message": "Detailed recommendation",
            "actions": ["Action 1", "Action 2"]
        }}
    ]
}}

Focus on actionable, specific advice. Don't provide medical diagnoses."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            ai_recs = []
            for i, rec in enumerate(result.get("recommendations", [])):
                ai_recs.append(Recommendation(
                    id=f"ai_{i}",
                    category=rec.get("category", "wellness"),
                    priority=rec.get("priority", "medium"),
                    title=rec.get("title", "Health Tip"),
                    message=rec.get("message", ""),
                    reasoning="AI-generated based on your health patterns",
                    source="ai",
                    confidence=0.75,
                    actions=rec.get("actions", [])
                ))
            
            return ai_recs
        except Exception:
            return []
    
    def _deduplicate_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Remove duplicate or overlapping recommendations"""
        seen_categories = {}
        unique_recs = []
        
        for rec in recommendations:
            key = (rec.category, rec.priority)
            if key not in seen_categories:
                seen_categories[key] = rec
                unique_recs.append(rec)
            elif rec.confidence > seen_categories[key].confidence:
                # Replace with higher confidence recommendation
                unique_recs.remove(seen_categories[key])
                seen_categories[key] = rec
                unique_recs.append(rec)
        
        return unique_recs
    
    def _prioritize_recommendations(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Sort recommendations by priority and confidence"""
        priority_order = {"high": 0, "medium": 1, "low": 2}
        
        return sorted(
            recommendations,
            key=lambda r: (priority_order.get(r.priority, 2), -r.confidence)
        )
