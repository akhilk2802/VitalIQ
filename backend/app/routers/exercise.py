from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date, timedelta
from collections import Counter
import uuid

from app.database import get_db
from app.models.user import User
from app.models.exercise_entry import ExerciseEntry
from app.schemas.exercise import (
    ExerciseEntryCreate, ExerciseEntryUpdate, ExerciseEntryResponse, WeeklyExerciseSummary
)
from app.utils.security import get_current_user
from app.utils.enums import ExerciseIntensity

router = APIRouter()


@router.get("", response_model=List[ExerciseEntryResponse])
async def get_exercise_entries(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get exercise entries for the current user"""
    query = select(ExerciseEntry).where(ExerciseEntry.user_id == current_user.id)
    
    if start_date:
        query = query.where(ExerciseEntry.date >= start_date)
    if end_date:
        query = query.where(ExerciseEntry.date <= end_date)
    
    query = query.order_by(ExerciseEntry.date.desc(), ExerciseEntry.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ExerciseEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_exercise_entry(
    entry_data: ExerciseEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new exercise entry"""
    entry = ExerciseEntry(
        user_id=current_user.id,
        **entry_data.model_dump()
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/weekly-summary", response_model=WeeklyExerciseSummary)
async def get_weekly_summary(
    week_offset: int = Query(0, ge=0, description="Weeks ago (0 = current week)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get exercise summary for a specific week"""
    today = date.today()
    
    # Calculate week start (Monday) and end (Sunday)
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday + (week_offset * 7))
    week_end = week_start + timedelta(days=6)
    
    query = select(ExerciseEntry).where(
        and_(
            ExerciseEntry.user_id == current_user.id,
            ExerciseEntry.date >= week_start,
            ExerciseEntry.date <= week_end
        )
    ).order_by(ExerciseEntry.date, ExerciseEntry.created_at)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Calculate totals
    total_duration = sum(e.duration_minutes for e in entries)
    total_calories = sum(e.calories_burned or 0 for e in entries)
    
    # Count workouts by type
    workouts_by_type = Counter(e.exercise_type.value for e in entries)
    
    # Calculate average intensity
    intensity_values = {
        ExerciseIntensity.low: 1,
        ExerciseIntensity.moderate: 2,
        ExerciseIntensity.high: 3,
        ExerciseIntensity.very_high: 4
    }
    
    if entries:
        avg_intensity_value = sum(intensity_values[e.intensity] for e in entries) / len(entries)
        if avg_intensity_value < 1.5:
            avg_intensity = "low"
        elif avg_intensity_value < 2.5:
            avg_intensity = "moderate"
        elif avg_intensity_value < 3.5:
            avg_intensity = "high"
        else:
            avg_intensity = "very_high"
    else:
        avg_intensity = "none"
    
    return WeeklyExerciseSummary(
        week_start=week_start,
        week_end=week_end,
        total_duration_minutes=total_duration,
        total_calories_burned=total_calories,
        workout_count=len(entries),
        workouts_by_type=dict(workouts_by_type),
        avg_intensity=avg_intensity,
        entries=entries
    )


@router.get("/{entry_id}", response_model=ExerciseEntryResponse)
async def get_exercise_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific exercise entry"""
    result = await db.execute(
        select(ExerciseEntry).where(
            and_(
                ExerciseEntry.id == entry_id,
                ExerciseEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise entry not found"
        )
    
    return entry


@router.put("/{entry_id}", response_model=ExerciseEntryResponse)
async def update_exercise_entry(
    entry_id: uuid.UUID,
    update_data: ExerciseEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an exercise entry"""
    result = await db.execute(
        select(ExerciseEntry).where(
            and_(
                ExerciseEntry.id == entry_id,
                ExerciseEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise entry not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)
    
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an exercise entry"""
    result = await db.execute(
        select(ExerciseEntry).where(
            and_(
                ExerciseEntry.id == entry_id,
                ExerciseEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise entry not found"
        )
    
    await db.delete(entry)
