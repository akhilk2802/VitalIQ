"""
Nutrition Data Normalizer

Transforms meal/nutrition data from external sources into VitalIQ's FoodEntry model.
"""
from datetime import datetime
from typing import Dict, Any

from app.models.food_entry import FoodEntry
from app.utils.enums import SyncDataType, DataSource, MealType
from app.integrations.normalizers.base import BaseNormalizer


class NutritionNormalizer(BaseNormalizer[FoodEntry]):
    """
    Normalizer for nutrition/meal data from external sources.
    
    Handles data from: MyFitnessPal, Cronometer, etc.
    """
    
    MODEL_CLASS = FoodEntry
    DATA_TYPE = SyncDataType.nutrition
    TARGET_TABLE = "food_entries"
    
    # Map external meal types to our MealType enum
    MEAL_TYPE_MAP = {
        "breakfast": MealType.breakfast,
        "lunch": MealType.lunch,
        "dinner": MealType.dinner,
        "snack": MealType.snack,
        "snacks": MealType.snack,
        "morning_snack": MealType.snack,
        "afternoon_snack": MealType.snack,
        "evening_snack": MealType.snack,
        "brunch": MealType.lunch,
        "supper": MealType.dinner,
    }
    
    def normalize_single(self, raw_data: Dict[str, Any], source: DataSource) -> FoodEntry:
        """
        Transform Vital meal data into FoodEntry.
        
        Vital meal data format:
        {
            "id": "meal_xxx",
            "calendar_date": "2024-01-15",
            "meal_type": "breakfast",
            "name": "Oatmeal with berries",
            "calories": 350,
            "protein_g": 12,
            "carbs_g": 55,
            "fat_g": 8,
            "fiber_g": 6,
            "sugar_g": 15,
            "sodium_mg": 120,
            "source": {"name": "MyFitnessPal", "slug": "myfitnesspal"}
        }
        """
        # Parse date
        calendar_date = self.parse_date(raw_data.get("calendar_date"))
        
        # Map meal type
        meal_type_str = raw_data.get("meal_type", "snack")
        meal_type = self._map_meal_type(meal_type_str)
        
        # Get food name
        food_name = raw_data.get("name") or f"{meal_type_str.title()} Entry"
        
        # Get macros
        calories = self.safe_float(raw_data.get("calories"), 0)
        protein_g = self.safe_float(raw_data.get("protein_g"), 0)
        carbs_g = self.safe_float(raw_data.get("carbs_g"), 0)
        fats_g = self.safe_float(raw_data.get("fat_g"), 0)  # Note: "fat_g" not "fats_g"
        sugar_g = self.safe_float(raw_data.get("sugar_g"), 0)
        fiber_g = self.safe_float(raw_data.get("fiber_g"))
        sodium_mg = self.safe_float(raw_data.get("sodium_mg"))
        
        # Get source name
        source_info = raw_data.get("source", {})
        source_name = source_info.get("slug", source.value) if isinstance(source_info, dict) else source.value
        
        return FoodEntry(
            user_id=self.user_id,
            date=calendar_date,
            meal_type=meal_type,
            food_name=food_name,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fats_g=fats_g,
            sugar_g=sugar_g,
            fiber_g=fiber_g if fiber_g and fiber_g > 0 else None,
            sodium_mg=sodium_mg if sodium_mg and sodium_mg > 0 else None,
            source=source_name,
            external_id=raw_data.get("id"),
            synced_at=datetime.utcnow()
        )
    
    def _map_meal_type(self, meal_type_str: str) -> MealType:
        """Map external meal type to our MealType enum."""
        meal_lower = meal_type_str.lower().replace(" ", "_")
        return self.MEAL_TYPE_MAP.get(meal_lower, MealType.snack)
