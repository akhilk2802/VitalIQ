from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
import uuid

from app.utils.enums import MealType


class FoodEntryCreate(BaseModel):
    date: date
    meal_type: MealType
    food_name: str = Field(..., min_length=1, max_length=255)
    calories: float = Field(..., ge=0)
    protein_g: float = Field(default=0, ge=0)
    carbs_g: float = Field(default=0, ge=0)
    fats_g: float = Field(default=0, ge=0)
    sugar_g: float = Field(default=0, ge=0)
    fiber_g: Optional[float] = Field(default=None, ge=0)
    sodium_mg: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class FoodEntryUpdate(BaseModel):
    meal_type: Optional[MealType] = None
    food_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    calories: Optional[float] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    fats_g: Optional[float] = Field(default=None, ge=0)
    sugar_g: Optional[float] = Field(default=None, ge=0)
    fiber_g: Optional[float] = Field(default=None, ge=0)
    sodium_mg: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None


class FoodEntryResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    meal_type: MealType
    food_name: str
    calories: float
    protein_g: float
    carbs_g: float
    fats_g: float
    sugar_g: float
    fiber_g: Optional[float]
    sodium_mg: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DailyNutritionSummary(BaseModel):
    date: date
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fats_g: float
    total_sugar_g: float
    total_fiber_g: float
    total_sodium_mg: float
    meal_count: int
    entries: List[FoodEntryResponse]
