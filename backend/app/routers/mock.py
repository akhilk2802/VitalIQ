from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, func
from typing import Optional, List, Any

from app.database import get_db
from app.models.user import User
from app.models.food_entry import FoodEntry
from app.models.sleep_entry import SleepEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.models.body_metrics import BodyMetrics
from app.models.chronic_metrics import ChronicMetrics
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.utils.security import get_current_user
from app.utils.mock_data import PersonaMockDataGenerator, PersonaType
from app.utils.enums import ConditionType

router = APIRouter()


@router.get("/personas")
async def list_personas():
    """List available persona types for mock data generation"""
    return {
        "personas": [
            {
                "id": PersonaType.active_athlete.value,
                "name": "Active Athlete",
                "description": "High exercise (6d/wk), good sleep, high protein, low resting HR"
            },
            {
                "id": PersonaType.poor_sleeper.value,
                "name": "Poor Sleeper",
                "description": "4-6hr sleep, high sugar cravings, elevated HR, poor recovery"
            },
            {
                "id": PersonaType.pre_diabetic.value,
                "name": "Pre-Diabetic",
                "description": "Elevated glucose, post-meal spikes, sugar cravings, moderate activity"
            },
            {
                "id": PersonaType.stress_prone.value,
                "name": "Stress-Prone",
                "description": "Weekly stress cycles, HRV drops, sleep disruption, comfort eating"
            },
            {
                "id": PersonaType.healthy_balanced.value,
                "name": "Healthy Balanced",
                "description": "Baseline reference - moderate everything, few anomalies"
            },
        ]
    }


@router.post("/generate")
async def generate_mock_data(
    days: int = Query(150, ge=7, le=365, description="Number of days of data to generate"),
    persona: PersonaType = Query(PersonaType.healthy_balanced, description="User persona for data patterns"),
    include_diabetes: bool = Query(True, description="Include diabetes/glucose metrics"),
    include_heart: bool = Query(False, description="Include heart/cholesterol metrics"),
    clear_existing: bool = Query(False, description="Clear existing data before generating"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate mock health data with realistic patterns based on persona.
    
    Personas embed realistic correlations:
    - Sleep quality affects next-day HRV and resting HR
    - Exercise improves same-day sleep quality
    - Low sleep triggers next-day sugar cravings
    - Sugar intake correlates with post-meal glucose spikes
    - Stress (low HRV) correlates with poor sleep
    """
    
    # Optionally clear existing data
    if clear_existing:
        await db.execute(delete(FoodEntry).where(FoodEntry.user_id == current_user.id))
        await db.execute(delete(SleepEntry).where(SleepEntry.user_id == current_user.id))
        await db.execute(delete(ExerciseEntry).where(ExerciseEntry.user_id == current_user.id))
        await db.execute(delete(VitalSigns).where(VitalSigns.user_id == current_user.id))
        await db.execute(delete(BodyMetrics).where(BodyMetrics.user_id == current_user.id))
        await db.execute(delete(ChronicMetrics).where(ChronicMetrics.user_id == current_user.id))
        await db.execute(delete(Anomaly).where(Anomaly.user_id == current_user.id))
        await db.execute(delete(Correlation).where(Correlation.user_id == current_user.id))
        await db.flush()
    
    # Generate data with selected persona
    generator = PersonaMockDataGenerator(
        user_id=current_user.id, 
        persona=persona,
        days=days
    )
    data = generator.generate_all()
    
    counts = {
        "food_entries": 0,
        "sleep_entries": 0,
        "exercise_entries": 0,
        "vital_signs": 0,
        "body_metrics": 0,
        "chronic_metrics": 0,
    }
    
    # Insert food entries
    for entry_data in data["food_entries"]:
        entry = FoodEntry(**entry_data)
        db.add(entry)
        counts["food_entries"] += 1
    
    # Insert sleep entries
    for entry_data in data["sleep_entries"]:
        entry = SleepEntry(**entry_data)
        db.add(entry)
        counts["sleep_entries"] += 1
    
    # Insert exercise entries
    for entry_data in data["exercise_entries"]:
        entry = ExerciseEntry(**entry_data)
        db.add(entry)
        counts["exercise_entries"] += 1
    
    # Insert vital signs
    for entry_data in data["vital_signs"]:
        entry = VitalSigns(**entry_data)
        db.add(entry)
        counts["vital_signs"] += 1
    
    # Insert body metrics
    for entry_data in data["body_metrics"]:
        entry = BodyMetrics(**entry_data)
        db.add(entry)
        counts["body_metrics"] += 1
    
    # Insert chronic metrics (diabetes)
    if include_diabetes:
        for entry_data in data["chronic_metrics"]:
            entry = ChronicMetrics(**entry_data)
            db.add(entry)
            counts["chronic_metrics"] += 1
    
    # Generate additional heart metrics if requested
    if include_heart:
        heart_data = generator.generate_chronic_metrics(ConditionType.heart)
        for entry_data in heart_data:
            entry = ChronicMetrics(**entry_data)
            db.add(entry)
            counts["chronic_metrics"] += 1
    
    await db.flush()
    
    return {
        "message": "Mock data generated successfully",
        "persona": persona.value,
        "persona_name": generator.config["name"],
        "days": days,
        "entries_created": counts,
        "total_entries": sum(counts.values()),
        "anomaly_days": list(generator.anomaly_days),
        "embedded_patterns": generator.get_embedded_patterns(),
        "data_cleared": clear_existing,
    }


@router.delete("/clear")
async def clear_all_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear all health data for the current user"""
    
    counts = {}
    
    # Delete in order to respect foreign keys
    result = await db.execute(delete(Anomaly).where(Anomaly.user_id == current_user.id))
    counts["anomalies"] = result.rowcount
    
    result = await db.execute(delete(Correlation).where(Correlation.user_id == current_user.id))
    counts["correlations"] = result.rowcount
    
    result = await db.execute(delete(FoodEntry).where(FoodEntry.user_id == current_user.id))
    counts["food_entries"] = result.rowcount
    
    result = await db.execute(delete(SleepEntry).where(SleepEntry.user_id == current_user.id))
    counts["sleep_entries"] = result.rowcount
    
    result = await db.execute(delete(ExerciseEntry).where(ExerciseEntry.user_id == current_user.id))
    counts["exercise_entries"] = result.rowcount
    
    result = await db.execute(delete(VitalSigns).where(VitalSigns.user_id == current_user.id))
    counts["vital_signs"] = result.rowcount
    
    result = await db.execute(delete(BodyMetrics).where(BodyMetrics.user_id == current_user.id))
    counts["body_metrics"] = result.rowcount
    
    result = await db.execute(delete(ChronicMetrics).where(ChronicMetrics.user_id == current_user.id))
    counts["chronic_metrics"] = result.rowcount
    
    await db.flush()
    
    return {
        "message": "All data cleared successfully",
        "deleted_counts": counts,
        "total_deleted": sum(counts.values()),
    }


@router.get("/data-summary")
async def get_user_data_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a comprehensive summary of all health data for the current user.
    Returns counts, date ranges, and recent records for each data type.
    """
    
    async def get_data_type_summary(model: Any, date_field: str, limit: int = 10) -> dict:
        """Helper to get summary for a data type"""
        # Get count
        count_result = await db.execute(
            select(func.count()).select_from(model).where(model.user_id == current_user.id)
        )
        count = count_result.scalar() or 0
        
        if count == 0:
            return {
                "count": 0,
                "first_date": None,
                "last_date": None,
                "recent": []
            }
        
        # Get date range
        date_col = getattr(model, date_field)
        min_date_result = await db.execute(
            select(func.min(date_col)).where(model.user_id == current_user.id)
        )
        max_date_result = await db.execute(
            select(func.max(date_col)).where(model.user_id == current_user.id)
        )
        first_date = min_date_result.scalar()
        last_date = max_date_result.scalar()
        
        # Get recent records
        recent_result = await db.execute(
            select(model)
            .where(model.user_id == current_user.id)
            .order_by(date_col.desc())
            .limit(limit)
        )
        recent_records = recent_result.scalars().all()
        
        # Convert to dict
        recent = []
        for record in recent_records:
            record_dict = {
                "id": str(record.id),
                date_field: str(getattr(record, date_field)) if getattr(record, date_field) else None
            }
            # Add type-specific fields - Food Entries
            if hasattr(record, 'food_name'):
                record_dict["food_name"] = record.food_name
            if hasattr(record, 'calories'):
                record_dict["calories"] = record.calories
            if hasattr(record, 'protein_g'):
                record_dict["protein_g"] = record.protein_g
            
            # Sleep Entries
            if hasattr(record, 'bedtime') and hasattr(record, 'wake_time'):
                record_dict["bedtime"] = str(record.bedtime) if record.bedtime else None
                record_dict["wake_time"] = str(record.wake_time) if record.wake_time else None
            if hasattr(record, 'duration_hours'):
                record_dict["duration_hours"] = record.duration_hours
            if hasattr(record, 'quality_score'):
                record_dict["quality_score"] = record.quality_score
            
            # Exercise Entries
            if hasattr(record, 'exercise_type'):
                record_dict["exercise_type"] = record.exercise_type.value if record.exercise_type else None
            if hasattr(record, 'exercise_name'):
                record_dict["exercise_name"] = record.exercise_name
            if hasattr(record, 'duration_minutes'):
                record_dict["duration_minutes"] = record.duration_minutes
            if hasattr(record, 'calories_burned'):
                record_dict["calories_burned"] = record.calories_burned
            
            # Vital Signs
            if hasattr(record, 'resting_heart_rate'):
                record_dict["resting_heart_rate"] = record.resting_heart_rate
            if hasattr(record, 'hrv_ms'):
                record_dict["hrv_ms"] = record.hrv_ms
            
            # Body Metrics
            if hasattr(record, 'weight_kg'):
                record_dict["weight_kg"] = record.weight_kg
            if hasattr(record, 'body_fat_pct'):
                record_dict["body_fat_pct"] = record.body_fat_pct
            
            # Chronic Metrics
            if hasattr(record, 'condition_type'):
                record_dict["condition_type"] = record.condition_type.value if record.condition_type else None
            if hasattr(record, 'blood_glucose_mgdl'):
                record_dict["blood_glucose_mgdl"] = record.blood_glucose_mgdl
            if hasattr(record, 'time_of_day') and hasattr(record, 'condition_type'):
                record_dict["time_of_day"] = record.time_of_day.value if record.time_of_day else None
            
            # Anomalies
            if hasattr(record, 'metric_name'):
                record_dict["metric_name"] = record.metric_name
            if hasattr(record, 'value'):
                record_dict["value"] = record.value
            if hasattr(record, 'severity'):
                record_dict["severity"] = record.severity.value if record.severity else None
            
            # Correlations
            if hasattr(record, 'metric_a') and hasattr(record, 'metric_b'):
                record_dict["metric_a"] = record.metric_a
                record_dict["metric_b"] = record.metric_b
            if hasattr(record, 'correlation_value'):
                record_dict["correlation_value"] = record.correlation_value
            if hasattr(record, 'strength'):
                record_dict["strength"] = record.strength.value if record.strength else None
            recent.append(record_dict)
        
        return {
            "count": count,
            "first_date": str(first_date) if first_date else None,
            "last_date": str(last_date) if last_date else None,
            "recent": recent
        }
    
    # Get summaries for each data type
    food_summary = await get_data_type_summary(FoodEntry, "date")
    sleep_summary = await get_data_type_summary(SleepEntry, "date")
    exercise_summary = await get_data_type_summary(ExerciseEntry, "date")
    vitals_summary = await get_data_type_summary(VitalSigns, "date")
    body_summary = await get_data_type_summary(BodyMetrics, "date")
    chronic_summary = await get_data_type_summary(ChronicMetrics, "date")
    anomalies_summary = await get_data_type_summary(Anomaly, "date")
    correlations_summary = await get_data_type_summary(Correlation, "detected_at")
    
    total_records = (
        food_summary["count"] +
        sleep_summary["count"] +
        exercise_summary["count"] +
        vitals_summary["count"] +
        body_summary["count"] +
        chronic_summary["count"] +
        anomalies_summary["count"] +
        correlations_summary["count"]
    )
    
    return {
        "food_entries": food_summary,
        "sleep_entries": sleep_summary,
        "exercise_entries": exercise_summary,
        "vital_signs": vitals_summary,
        "body_metrics": body_summary,
        "chronic_metrics": chronic_summary,
        "anomalies": anomalies_summary,
        "correlations": correlations_summary,
        "total_records": total_records
    }
