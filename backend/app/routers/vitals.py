from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date
import uuid

from app.database import get_db
from app.models.user import User
from app.models.vital_signs import VitalSigns
from app.schemas.vitals import VitalSignsCreate, VitalSignsUpdate, VitalSignsResponse
from app.utils.security import get_current_user

router = APIRouter()


@router.get("", response_model=List[VitalSignsResponse])
async def get_vital_signs(
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get vital signs for the current user"""
    query = select(VitalSigns).where(VitalSigns.user_id == current_user.id)
    
    if start_date:
        query = query.where(VitalSigns.date >= start_date)
    if end_date:
        query = query.where(VitalSigns.date <= end_date)
    
    query = query.order_by(VitalSigns.date.desc(), VitalSigns.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=VitalSignsResponse, status_code=status.HTTP_201_CREATED)
async def create_vital_signs(
    entry_data: VitalSignsCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vital signs entry"""
    entry = VitalSigns(
        user_id=current_user.id,
        **entry_data.model_dump()
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=VitalSignsResponse)
async def get_vital_signs_entry(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vital signs entry"""
    result = await db.execute(
        select(VitalSigns).where(
            and_(
                VitalSigns.id == entry_id,
                VitalSigns.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vital signs entry not found"
        )
    
    return entry


@router.put("/{entry_id}", response_model=VitalSignsResponse)
async def update_vital_signs(
    entry_id: uuid.UUID,
    update_data: VitalSignsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a vital signs entry"""
    result = await db.execute(
        select(VitalSigns).where(
            and_(
                VitalSigns.id == entry_id,
                VitalSigns.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vital signs entry not found"
        )
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)
    
    await db.flush()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vital_signs(
    entry_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a vital signs entry"""
    result = await db.execute(
        select(VitalSigns).where(
            and_(
                VitalSigns.id == entry_id,
                VitalSigns.user_id == current_user.id
            )
        )
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vital signs entry not found"
        )
    
    await db.delete(entry)
