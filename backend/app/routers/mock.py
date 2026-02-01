from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.food_entry import FoodEntry
from app.models.sleep_entry import SleepEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.models.body_metrics import BodyMetrics
from app.models.chronic_metrics import ChronicMetrics
from app.utils.security import get_current_user
from app.utils.mock_data import MockDataGenerator

router = APIRouter()


@router.post("/generate")
async def generate_mock_data(
    days: int = Query(60, ge=7, le=365, description="Number of days of data to generate"),
    include_diabetes: bool = Query(True, description="Include diabetes metrics"),
    include_heart: bool = Query(False, description="Include heart/cholesterol metrics"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate mock health data for testing and demo purposes"""
    
    generator = MockDataGenerator(user_id=current_user.id, days=days)
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
        from app.utils.enums import ConditionType
        heart_data = generator.generate_chronic_metrics(ConditionType.heart)
        for entry_data in heart_data:
            entry = ChronicMetrics(**entry_data)
            db.add(entry)
            counts["chronic_metrics"] += 1
    
    await db.flush()
    
    return {
        "message": "Mock data generated successfully",
        "days": days,
        "entries_created": counts,
        "total_entries": sum(counts.values()),
        "anomaly_days": generator.anomaly_days,
    }
