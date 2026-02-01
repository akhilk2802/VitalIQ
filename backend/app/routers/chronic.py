from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.models.chronic_metrics import ChronicMetrics
from app.schemas.chronic import (
    ChronicMetricsCreate, ChronicMetricsUpdate, ChronicMetricsResponse, 
    ChronicTrends, ChronicTrendData
)
from app.utils.security import get_current_user
from app.utils.enums import ConditionType

router = APIRouter()


@router.get("", response_model=List[ChronicMetricsResponse])
async def get_chronic_metrics(
    condition_type: Optional[ConditionType] = Query(None, description="Filter by condition type"),
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chronic health metrics for the current user"""
    query = select(ChronicMetrics).where(ChronicMetrics.user_id == current_user.id)
    
    if condition_type:
        query = query.where(ChronicMetrics.condition_type == condition_type)
    if start_date:
        query = query.where(ChronicMetrics.date >= start_date)
    if end_date:
        query = query.where(ChronicMetrics.date <= end_date)
    
    query = query.order_by(ChronicMetrics.date.desc(), ChronicMetrics.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ChronicMetricsResponse, status_code=status.HTTP_201_CREATED)
async def create_chronic_metrics(
    entry_data: ChronicMetricsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chronic health metrics entry"""
    entry = ChronicMetrics(
        user_id=current_user.id,
        **entry_data.model_dump()
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/trends", response_model=ChronicTrends)
async def get_chronic_trends(
    condition_type: ConditionType = Query(..., description="Condition type to analyze"),
    metric_name: str = Query(..., description="Metric name (e.g., blood_glucose_mgdl, cholesterol_total)"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get trend data for a specific chronic health metric"""
    from datetime import timedelta
    
    start_date = date.today() - timedelta(days=days)
    
    # Validate metric name
    valid_metrics = [
        'blood_glucose_mgdl', 'insulin_units', 'hba1c_pct',
        'cholesterol_total', 'cholesterol_ldl', 'cholesterol_hdl', 'triglycerides'
    ]
    
    if metric_name not in valid_metrics:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric name. Valid options: {valid_metrics}"
        )
    
    query = select(ChronicMetrics).where(
        and_(
            ChronicMetrics.user_id == current_user.id,
            ChronicMetrics.condition_type == condition_type,
            ChronicMetrics.date >= start_date
        )
    ).order_by(ChronicMetrics.date)
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Extract values for the specific metric
    data = []
    values = []
    
    for entry in entries:
        value = getattr(entry, metric_name)
        if value is not None:
            data.append(ChronicTrendData(
                date=entry.date,
                value=value,
                time_of_day=entry.time_of_day
            ))
            values.append(value)
    
    if not values:
        return ChronicTrends(
            condition_type=condition_type,
            metric_name=metric_name,
            data=[],
            avg_value=0,
            min_value=0,
            max_value=0
        )
    
    return ChronicTrends(
        condition_type=condition_type,
        metric_name=metric_name,
        data=data,
        avg_value=round(sum(values) / len(values), 2),
        min_value=min(values),
        max_value=max(values)
    )


@router.get("/{entry_id}", response_model=ChronicMetricsResponse)
async def get_chronic_metrics_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chronic health metrics entry"""
    result = await db.execute(
        select(ChronicMetrics).where(
            and_(
                ChronicMetrics.id == entry_id,
                ChronicMetrics.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chronic metrics entry not found"
        )
    
    return entry


@router.put("/{entry_id}", response_model=ChronicMetricsResponse)
async def update_chronic_metrics(
    entry_id: uuid.UUID,
    update_data: ChronicMetricsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a chronic health metrics entry"""
    result = await db.execute(
        select(ChronicMetrics).where(
            and_(
                ChronicMetrics.id == entry_id,
                ChronicMetrics.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chronic metrics entry not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)
    
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chronic_metrics(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a chronic health metrics entry"""
    result = await db.execute(
        select(ChronicMetrics).where(
            and_(
                ChronicMetrics.id == entry_id,
                ChronicMetrics.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chronic metrics entry not found"
        )
    
    await db.delete(entry)
