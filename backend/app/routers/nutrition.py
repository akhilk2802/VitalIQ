from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.models.food_entry import FoodEntry
from app.schemas.food import (
    FoodEntryCreate, FoodEntryUpdate, FoodEntryResponse, DailyNutritionSummary
)
from app.utils.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[FoodEntryResponse])
async def get_food_entries(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get food entries for the current user"""
    query = select(FoodEntry).where(FoodEntry.user_id == current_user.id)
    
    if start_date:
        query = query.where(FoodEntry.date >= start_date)
    if end_date:
        query = query.where(FoodEntry.date <= end_date)
    
    query = query.order_by(FoodEntry.date.desc(), FoodEntry.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=FoodEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_food_entry(
    entry_data: FoodEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new food entry"""
    entry = FoodEntry(
        user_id=current_user.id,
        **entry_data.model_dump()
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/daily-summary", response_model=DailyNutritionSummary)
async def get_daily_summary(
    target_date: date = Query(..., description="Date to get summary for"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get nutrition summary for a specific day"""
    query = select(FoodEntry).where(
        and_(
            FoodEntry.user_id == current_user.id,
            FoodEntry.date == target_date
        )
    ).order_by(FoodEntry.created_at)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Calculate totals
    total_calories = sum(e.calories for e in entries)
    total_protein = sum(e.protein_g for e in entries)
    total_carbs = sum(e.carbs_g for e in entries)
    total_fats = sum(e.fats_g for e in entries)
    total_sugar = sum(e.sugar_g for e in entries)
    total_fiber = sum(e.fiber_g or 0 for e in entries)
    total_sodium = sum(e.sodium_mg or 0 for e in entries)
    
    return DailyNutritionSummary(
        date=target_date,
        total_calories=total_calories,
        total_protein_g=total_protein,
        total_carbs_g=total_carbs,
        total_fats_g=total_fats,
        total_sugar_g=total_sugar,
        total_fiber_g=total_fiber,
        total_sodium_mg=total_sodium,
        meal_count=len(entries),
        entries=entries
    )


@router.get("/{entry_id}", response_model=FoodEntryResponse)
async def get_food_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific food entry"""
    result = await db.execute(
        select(FoodEntry).where(
            and_(
                FoodEntry.id == entry_id,
                FoodEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food entry not found"
        )
    
    return entry


@router.put("/{entry_id}", response_model=FoodEntryResponse)
async def update_food_entry(
    entry_id: uuid.UUID,
    update_data: FoodEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a food entry"""
    result = await db.execute(
        select(FoodEntry).where(
            and_(
                FoodEntry.id == entry_id,
                FoodEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food entry not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)
    
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a food entry"""
    result = await db.execute(
        select(FoodEntry).where(
            and_(
                FoodEntry.id == entry_id,
                FoodEntry.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food entry not found"
        )
    
    await db.delete(entry)
