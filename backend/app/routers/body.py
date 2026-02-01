from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.models.body_metrics import BodyMetrics
from app.schemas.body import BodyMetricsCreate, BodyMetricsUpdate, BodyMetricsResponse
from app.utils.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[BodyMetricsResponse])
async def get_body_metrics(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get body metrics for the current user"""
    query = select(BodyMetrics).where(BodyMetrics.user_id == current_user.id)
    
    if start_date:
        query = query.where(BodyMetrics.date >= start_date)
    if end_date:
        query = query.where(BodyMetrics.date <= end_date)
    
    query = query.order_by(BodyMetrics.date.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=BodyMetricsResponse, status_code=status.HTTP_201_CREATED)
async def create_body_metrics(
    entry_data: BodyMetricsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new body metrics entry"""
    entry = BodyMetrics(
        user_id=current_user.id,
        **entry_data.model_dump()
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=BodyMetricsResponse)
async def get_body_metrics_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific body metrics entry"""
    result = await db.execute(
        select(BodyMetrics).where(
            and_(
                BodyMetrics.id == entry_id,
                BodyMetrics.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Body metrics entry not found"
        )
    
    return entry


@router.put("/{entry_id}", response_model=BodyMetricsResponse)
async def update_body_metrics(
    entry_id: uuid.UUID,
    update_data: BodyMetricsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a body metrics entry"""
    result = await db.execute(
        select(BodyMetrics).where(
            and_(
                BodyMetrics.id == entry_id,
                BodyMetrics.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Body metrics entry not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)
    
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_body_metrics(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a body metrics entry"""
    result = await db.execute(
        select(BodyMetrics).where(
            and_(
                BodyMetrics.id == entry_id,
                BodyMetrics.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Body metrics entry not found"
        )
    
    await db.delete(entry)
