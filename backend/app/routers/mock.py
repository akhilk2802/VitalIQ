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
