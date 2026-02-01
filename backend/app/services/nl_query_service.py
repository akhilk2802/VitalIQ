"""
Natural Language Query Service

Handles natural language queries about health data using GPT-4 function calling.
Supports:
- Data retrieval: "What was my avg sleep last week?"
- Insights: "Why was my glucose high yesterday?"
- Recommendations: "What should I eat today?"
- Comparisons: "How does this week compare to last month?"
"""

from typing import List, Dict, Optional, Any, Callable
from datetime import date, timedelta
from dataclasses import dataclass
import json
import uuid
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from openai import AsyncOpenAI

from app.config import settings
from app.models.sleep_entry import SleepEntry
from app.models.food_entry import FoodEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.models.body_metrics import BodyMetrics
from app.models.chronic_metrics import ChronicMetrics
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.ml.prediction.recovery import RecoveryPredictor
from app.ml.prediction.cravings import CravingsPredictor
from app.services.recommendation_service import RecommendationService


class QueryIntent(str, Enum):
    """Classified query intents"""
    DATA_RETRIEVAL = "data_retrieval"
    INSIGHT = "insight"
    RECOMMENDATION = "recommendation"
    COMPARISON = "comparison"
    PREDICTION = "prediction"
    GENERAL = "general"


@dataclass
class QueryResult:
    """Result of a natural language query"""
    query: str
    intent: QueryIntent
    answer: str
    data: Optional[Dict[str, Any]] = None
    confidence: float = 0.8
    follow_up_suggestions: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent.value,
            "answer": self.answer,
            "data": self.data,
            "confidence": round(self.confidence, 2),
            "follow_up_suggestions": self.follow_up_suggestions or []
        }


class NLQueryService:
    """Natural language query processor for health data"""
    
    # Available functions for GPT-4 function calling
    FUNCTIONS = [
        {
            "name": "get_sleep_data",
            "description": "Get sleep data for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                    "metric": {"type": "string", "enum": ["duration", "quality", "deep_sleep", "all"]}
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_nutrition_data",
            "description": "Get nutrition/food data for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "metric": {"type": "string", "enum": ["calories", "protein", "carbs", "sugar", "all"]}
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_exercise_data",
            "description": "Get exercise/workout data for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "metric": {"type": "string", "enum": ["duration", "calories", "frequency", "all"]}
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_vitals_data",
            "description": "Get vital signs (heart rate, HRV, blood pressure)",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "metric": {"type": "string", "enum": ["resting_hr", "hrv", "blood_pressure", "all"]}
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_glucose_data",
            "description": "Get blood glucose data",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "time_of_day": {"type": "string", "enum": ["fasting", "post_meal", "all"]}
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_anomalies",
            "description": "Get detected anomalies",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "metric_name": {"type": "string", "description": "Filter by metric name (optional)"}
                },
                "required": ["start_date", "end_date"]
            }
        },
        {
            "name": "get_correlations",
            "description": "Get detected correlations between metrics",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "description": "Filter by metric involved (optional)"},
                    "actionable_only": {"type": "boolean", "default": True}
                }
            }
        },
        {
            "name": "get_recovery_prediction",
            "description": "Get recovery readiness prediction for today",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_craving_prediction",
            "description": "Get food craving prediction for today",
            "parameters": {"type": "object", "properties": {}}
        },
        {
            "name": "get_recommendations",
            "description": "Get personalized health recommendations",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["exercise", "nutrition", "sleep", "all"]}
                }
            }
        },
        {
            "name": "compare_periods",
            "description": "Compare health metrics between two time periods",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["sleep", "exercise", "nutrition", "vitals", "all"]},
                    "period1_start": {"type": "string"},
                    "period1_end": {"type": "string"},
                    "period2_start": {"type": "string"},
                    "period2_end": {"type": "string"}
                },
                "required": ["metric", "period1_start", "period1_end", "period2_start", "period2_end"]
            }
        }
    ]
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def query(self, user_query: str) -> QueryResult:
        """
        Process a natural language query and return results.
        
        Args:
            user_query: Natural language query from user
        
        Returns:
            QueryResult with answer and relevant data
        """
        if not self.openai_client:
            return QueryResult(
                query=user_query,
                intent=QueryIntent.GENERAL,
                answer="Natural language queries require OpenAI API key to be configured.",
                confidence=0.0
            )
        
        # Step 1: Use GPT-4 to understand query and call appropriate functions
        messages = [
            {
                "role": "system",
                "content": """You are a health data assistant. Analyze the user's query and call the appropriate functions to gather data.
Then provide a helpful, conversational answer based on the data.
Today's date is """ + date.today().isoformat() + """.
When interpreting dates:
- "last week" = past 7 days
- "this month" = from start of current month
- "yesterday" = yesterday's date
- "today" = today's date"""
            },
            {"role": "user", "content": user_query}
        ]
        
        try:
            # First call - determine what data to fetch
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                tools=[{"type": "function", "function": f} for f in self.FUNCTIONS],
                tool_choice="auto"
            )
            
            # Process function calls
            assistant_message = response.choices[0].message
            collected_data = {}
            
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    # Execute the function
                    result = await self._execute_function(function_name, arguments)
                    collected_data[function_name] = result
                
                # Add function results to messages
                messages.append(assistant_message)
                for tool_call in assistant_message.tool_calls:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(collected_data.get(tool_call.function.name, {}))
                    })
                
                # Second call - generate final answer
                final_response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    max_tokens=500
                )
                
                answer = final_response.choices[0].message.content
            else:
                answer = assistant_message.content or "I couldn't understand your query. Please try rephrasing."
            
            # Determine intent from function calls
            intent = self._classify_intent(
                [tc.function.name for tc in (assistant_message.tool_calls or [])]
            )
            
            # Generate follow-up suggestions
            follow_ups = self._generate_follow_ups(intent, user_query)
            
            return QueryResult(
                query=user_query,
                intent=intent,
                answer=answer,
                data=collected_data if collected_data else None,
                confidence=0.85,
                follow_up_suggestions=follow_ups
            )
            
        except Exception as e:
            return QueryResult(
                query=user_query,
                intent=QueryIntent.GENERAL,
                answer=f"I encountered an error processing your query. Please try again or rephrase your question.",
                confidence=0.0
            )
    
    async def _execute_function(self, function_name: str, arguments: Dict) -> Dict[str, Any]:
        """Execute a function and return results"""
        
        if function_name == "get_sleep_data":
            return await self._get_sleep_data(**arguments)
        elif function_name == "get_nutrition_data":
            return await self._get_nutrition_data(**arguments)
        elif function_name == "get_exercise_data":
            return await self._get_exercise_data(**arguments)
        elif function_name == "get_vitals_data":
            return await self._get_vitals_data(**arguments)
        elif function_name == "get_glucose_data":
            return await self._get_glucose_data(**arguments)
        elif function_name == "get_anomalies":
            return await self._get_anomalies(**arguments)
        elif function_name == "get_correlations":
            return await self._get_correlations(**arguments)
        elif function_name == "get_recovery_prediction":
            return await self._get_recovery_prediction()
        elif function_name == "get_craving_prediction":
            return await self._get_craving_prediction()
        elif function_name == "get_recommendations":
            return await self._get_recommendations(**arguments)
        elif function_name == "compare_periods":
            return await self._compare_periods(**arguments)
        
        return {"error": f"Unknown function: {function_name}"}
    
    async def _get_sleep_data(
        self, 
        start_date: str, 
        end_date: str, 
        metric: str = "all"
    ) -> Dict[str, Any]:
        """Get sleep data for date range"""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        result = await self.db.execute(
            select(SleepEntry)
            .where(and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date >= start,
                SleepEntry.date <= end
            ))
            .order_by(SleepEntry.date)
        )
        entries = result.scalars().all()
        
        if not entries:
            return {"message": "No sleep data found for this period", "entries": 0}
        
        data = {
            "entries": len(entries),
            "date_range": f"{start_date} to {end_date}"
        }
        
        durations = [e.duration_hours for e in entries if e.duration_hours]
        qualities = [e.quality_score for e in entries if e.quality_score]
        
        if durations:
            data["avg_duration_hours"] = round(sum(durations) / len(durations), 2)
            data["min_duration"] = round(min(durations), 2)
            data["max_duration"] = round(max(durations), 2)
        
        if qualities:
            data["avg_quality_score"] = round(sum(qualities) / len(qualities), 1)
        
        return data
    
    async def _get_nutrition_data(
        self, 
        start_date: str, 
        end_date: str, 
        metric: str = "all"
    ) -> Dict[str, Any]:
        """Get nutrition data for date range"""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        result = await self.db.execute(
            select(
                func.count(FoodEntry.id).label("entries"),
                func.sum(FoodEntry.calories).label("total_calories"),
                func.sum(FoodEntry.protein_g).label("total_protein"),
                func.sum(FoodEntry.carbs_g).label("total_carbs"),
                func.sum(FoodEntry.sugar_g).label("total_sugar")
            )
            .where(and_(
                FoodEntry.user_id == self.user_id,
                FoodEntry.date >= start,
                FoodEntry.date <= end
            ))
        )
        row = result.one()
        
        days = (end - start).days + 1
        
        return {
            "date_range": f"{start_date} to {end_date}",
            "total_entries": row.entries or 0,
            "avg_daily_calories": round((row.total_calories or 0) / days, 0),
            "avg_daily_protein_g": round((row.total_protein or 0) / days, 1),
            "avg_daily_carbs_g": round((row.total_carbs or 0) / days, 1),
            "avg_daily_sugar_g": round((row.total_sugar or 0) / days, 1)
        }
    
    async def _get_exercise_data(
        self, 
        start_date: str, 
        end_date: str, 
        metric: str = "all"
    ) -> Dict[str, Any]:
        """Get exercise data for date range"""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        result = await self.db.execute(
            select(ExerciseEntry)
            .where(and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= start,
                ExerciseEntry.date <= end
            ))
        )
        entries = result.scalars().all()
        
        if not entries:
            return {"message": "No exercise data found", "workouts": 0}
        
        days = (end - start).days + 1
        active_days = len(set(e.date for e in entries))
        total_minutes = sum(e.duration_minutes or 0 for e in entries)
        total_calories = sum(e.calories_burned or 0 for e in entries)
        
        return {
            "date_range": f"{start_date} to {end_date}",
            "total_workouts": len(entries),
            "active_days": active_days,
            "active_day_percentage": round(active_days / days * 100, 1),
            "total_minutes": total_minutes,
            "avg_daily_minutes": round(total_minutes / days, 1),
            "total_calories_burned": total_calories
        }
    
    async def _get_vitals_data(
        self, 
        start_date: str, 
        end_date: str, 
        metric: str = "all"
    ) -> Dict[str, Any]:
        """Get vitals data for date range"""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        result = await self.db.execute(
            select(VitalSigns)
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= start,
                VitalSigns.date <= end
            ))
        )
        entries = result.scalars().all()
        
        if not entries:
            return {"message": "No vitals data found", "entries": 0}
        
        hr_values = [e.resting_heart_rate for e in entries if e.resting_heart_rate]
        hrv_values = [e.hrv_ms for e in entries if e.hrv_ms]
        
        data = {
            "date_range": f"{start_date} to {end_date}",
            "entries": len(entries)
        }
        
        if hr_values:
            data["avg_resting_hr"] = round(sum(hr_values) / len(hr_values), 1)
            data["min_resting_hr"] = min(hr_values)
            data["max_resting_hr"] = max(hr_values)
        
        if hrv_values:
            data["avg_hrv_ms"] = round(sum(hrv_values) / len(hrv_values), 1)
        
        return data
    
    async def _get_glucose_data(
        self, 
        start_date: str, 
        end_date: str, 
        time_of_day: str = "all"
    ) -> Dict[str, Any]:
        """Get glucose data for date range"""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        query = select(ChronicMetrics).where(and_(
            ChronicMetrics.user_id == self.user_id,
            ChronicMetrics.date >= start,
            ChronicMetrics.date <= end,
            ChronicMetrics.blood_glucose_mgdl.isnot(None)
        ))
        
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return {"message": "No glucose data found", "readings": 0}
        
        fasting = [e.blood_glucose_mgdl for e in entries if e.time_of_day and e.time_of_day.value == "fasting"]
        post_meal = [e.blood_glucose_mgdl for e in entries if e.time_of_day and e.time_of_day.value == "post_meal"]
        
        data = {
            "date_range": f"{start_date} to {end_date}",
            "total_readings": len(entries)
        }
        
        if fasting:
            data["avg_fasting_glucose"] = round(sum(fasting) / len(fasting), 1)
            data["fasting_readings"] = len(fasting)
        
        if post_meal:
            data["avg_post_meal_glucose"] = round(sum(post_meal) / len(post_meal), 1)
            data["post_meal_readings"] = len(post_meal)
        
        return data
    
    async def _get_anomalies(
        self, 
        start_date: str, 
        end_date: str, 
        metric_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get anomalies for date range"""
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        
        query = select(Anomaly).where(and_(
            Anomaly.user_id == self.user_id,
            Anomaly.date >= start,
            Anomaly.date <= end
        ))
        
        if metric_name:
            query = query.where(Anomaly.metric_name.ilike(f"%{metric_name}%"))
        
        result = await self.db.execute(query.order_by(Anomaly.date.desc()))
        anomalies = result.scalars().all()
        
        if not anomalies:
            return {"message": "No anomalies detected in this period", "count": 0}
        
        return {
            "count": len(anomalies),
            "anomalies": [
                {
                    "date": a.date.isoformat(),
                    "metric": a.metric_name,
                    "value": a.metric_value,
                    "baseline": a.baseline_value,
                    "severity": a.severity.value,
                    "explanation": a.explanation
                }
                for a in anomalies[:10]  # Limit to 10
            ]
        }
    
    async def _get_correlations(
        self, 
        metric: Optional[str] = None, 
        actionable_only: bool = True
    ) -> Dict[str, Any]:
        """Get correlations"""
        query = select(Correlation).where(Correlation.user_id == self.user_id)
        
        if actionable_only:
            query = query.where(Correlation.is_actionable == True)
        
        if metric:
            query = query.where(
                (Correlation.metric_a.ilike(f"%{metric}%")) | 
                (Correlation.metric_b.ilike(f"%{metric}%"))
            )
        
        result = await self.db.execute(
            query.order_by(Correlation.confidence_score.desc()).limit(10)
        )
        correlations = result.scalars().all()
        
        if not correlations:
            return {"message": "No correlations found", "count": 0}
        
        return {
            "count": len(correlations),
            "correlations": [
                {
                    "metrics": f"{c.metric_a} ↔ {c.metric_b}",
                    "type": c.correlation_type.value,
                    "strength": c.strength.value,
                    "insight": c.insight,
                    "recommendation": c.recommendation
                }
                for c in correlations
            ]
        }
    
    async def _get_recovery_prediction(self) -> Dict[str, Any]:
        """Get today's recovery prediction"""
        predictor = RecoveryPredictor(self.db, self.user_id)
        result = await predictor.predict()
        return result.to_dict()
    
    async def _get_craving_prediction(self) -> Dict[str, Any]:
        """Get today's craving prediction"""
        predictor = CravingsPredictor(self.db, self.user_id)
        result = await predictor.predict()
        return result.to_dict()
    
    async def _get_recommendations(
        self, 
        category: str = "all"
    ) -> Dict[str, Any]:
        """Get recommendations"""
        service = RecommendationService(self.db, self.user_id)
        recommendations = await service.get_recommendations(include_ai=False)
        
        if category != "all":
            recommendations = [r for r in recommendations if r.category == category]
        
        return {
            "count": len(recommendations),
            "recommendations": [r.to_dict() for r in recommendations[:5]]
        }
    
    async def _compare_periods(
        self,
        metric: str,
        period1_start: str,
        period1_end: str,
        period2_start: str,
        period2_end: str
    ) -> Dict[str, Any]:
        """Compare metrics between two periods"""
        
        if metric == "sleep":
            p1 = await self._get_sleep_data(period1_start, period1_end)
            p2 = await self._get_sleep_data(period2_start, period2_end)
        elif metric == "exercise":
            p1 = await self._get_exercise_data(period1_start, period1_end)
            p2 = await self._get_exercise_data(period2_start, period2_end)
        elif metric == "nutrition":
            p1 = await self._get_nutrition_data(period1_start, period1_end)
            p2 = await self._get_nutrition_data(period2_start, period2_end)
        elif metric == "vitals":
            p1 = await self._get_vitals_data(period1_start, period1_end)
            p2 = await self._get_vitals_data(period2_start, period2_end)
        else:
            return {"error": f"Unknown metric: {metric}"}
        
        return {
            "metric": metric,
            "period1": {"range": f"{period1_start} to {period1_end}", "data": p1},
            "period2": {"range": f"{period2_start} to {period2_end}", "data": p2}
        }
    
    def _classify_intent(self, function_names: List[str]) -> QueryIntent:
        """Classify intent based on functions called"""
        if not function_names:
            return QueryIntent.GENERAL
        
        if "compare_periods" in function_names:
            return QueryIntent.COMPARISON
        elif "get_recovery_prediction" in function_names or "get_craving_prediction" in function_names:
            return QueryIntent.PREDICTION
        elif "get_recommendations" in function_names:
            return QueryIntent.RECOMMENDATION
        elif "get_anomalies" in function_names or "get_correlations" in function_names:
            return QueryIntent.INSIGHT
        else:
            return QueryIntent.DATA_RETRIEVAL
    
    def _generate_follow_ups(self, intent: QueryIntent, query: str) -> List[str]:
        """Generate follow-up question suggestions"""
        follow_ups = {
            QueryIntent.DATA_RETRIEVAL: [
                "How does this compare to last week?",
                "What factors might have affected these numbers?",
                "Any recommendations based on this data?"
            ],
            QueryIntent.INSIGHT: [
                "What should I do about this?",
                "Are there any patterns I should watch?",
                "How can I improve these metrics?"
            ],
            QueryIntent.RECOMMENDATION: [
                "Why is this recommended?",
                "What's my current status in this area?",
                "Show me my recent data for context"
            ],
            QueryIntent.COMPARISON: [
                "What caused these differences?",
                "Which period was better overall?",
                "Any recommendations for improvement?"
            ],
            QueryIntent.PREDICTION: [
                "What factors are affecting this prediction?",
                "How can I improve my score?",
                "Show me my recent sleep/exercise data"
            ],
            QueryIntent.GENERAL: [
                "Show me my sleep data from last week",
                "How am I doing with exercise?",
                "Any health recommendations for today?"
            ]
        }
        
        return follow_ups.get(intent, follow_ups[QueryIntent.GENERAL])[:3]
