from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.models.sleep_entry import SleepEntry
from app.schemas.sleep import (
    SleepEntryCreate, SleepEntryUpdate, SleepEntryResponse, SleepStats
)
from app.utils.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[SleepEntryResponse])
async def get_sleep_entries(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sleep entries for the current user"""
    query = select(SleepEntry).where(SleepEntry.user_id == current_user.id)
    
    if start_date:
        query = query.where(SleepEntry.date >= start_date)
    if end_date:
        query = query.where(SleepEntry.date <= end_date)
    
    query = query.order_by(SleepEntry.date.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=SleepEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_sleep_entry(
    entry_data: SleepEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new sleep entry"""
    # Calculate duration
    duration_hours = (entry_data.wake_time - entry_data.bedtime).total_seconds() / 3600
    
    entry = SleepEntry(
        user_id=current_user.id,
        duration_hours=duration_hours,
        **entry_data.model_dump()
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/stats", response_model=SleepStats)
async def get_sleep_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sleep statistics for the user"""
    from datetime import timedelta
    
    start_date = date.today() - timedelta(days=days)
    
    query = select(SleepEntry).where(
        and_(
            SleepEntry.user_id == current_user.id,
            SleepEntry.date >= start_date
        )
    ).order_by(SleepEntry.quality_score.desc())
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    if not entries:
        return SleepStats(
            avg_duration_hours=0,
            avg_quality_score=0,
            avg_deep_sleep_minutes=None,
            avg_rem_sleep_minutes=None,
            total_entries=0,
            best_sleep_date=None,
            worst_sleep_date=None
        )
    
    # Calculate averages
    avg_duration = sum(e.duration_hours for e in entries) / len(entries)
    avg_quality = sum(e.quality_score for e in entries) / len(entries)
    
    deep_sleep_entries = [e.deep_sleep_minutes for e in entries if e.deep_sleep_minutes is not None]
    avg_deep_sleep = sum(deep_sleep_entries) / len(deep_sleep_entries) if deep_sleep_entries else None
    
    rem_sleep_entries = [e.rem_sleep_minutes for e in entries if e.rem_sleep_minutes is not None]
    avg_rem_sleep = sum(rem_sleep_entries) / len(rem_sleep_entries) if rem_sleep_entries else None
    
    # Best and worst sleep dates
    best_entry = max(entries, key=lambda e: e.quality_score)
    worst_entry = min(entries, key=lambda e: e.quality_score)
    
    return SleepStats(
        avg_duration_hours=round(avg_duration, 2),
        avg_quality_score=round(avg_quality, 1),
        avg_deep_sleep_minutes=round(avg_deep_sleep, 1) if avg_deep_sleep else None,
        avg_rem_sleep_minutes=round(avg_rem_sleep, 1) if avg_rem_sleep else None,
        total_entries=len(entries),
        best_sleep_date=best_entry.date,
        worst_sleep_date=worst_entry.date
    )


@router.get("/{entry_id}", response_model=SleepEntryResponse)
async def get_sleep_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific sleep entry"""
    result = await db.execute(
        select(SleepEntry).where(
            and_(
                SleepEntry.id == entry_id,
                SleepEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sleep entry not found"
        )
    
    return entry


@router.put("/{entry_id}", response_model=SleepEntryResponse)
async def update_sleep_entry(
    entry_id: uuid.UUID,
    update_data: SleepEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a sleep entry"""
    result = await db.execute(
        select(SleepEntry).where(
            and_(
                SleepEntry.id == entry_id,
                SleepEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sleep entry not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)
    
    # Recalculate duration if times changed
    if 'bedtime' in update_dict or 'wake_time' in update_dict:
        entry.duration_hours = (entry.wake_time - entry.bedtime).total_seconds() / 3600
    
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sleep_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a sleep entry"""
    result = await db.execute(
        select(SleepEntry).where(
            and_(
                SleepEntry.id == entry_id,
                SleepEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sleep entry not found"
        )
    
    await db.delete(entry)
