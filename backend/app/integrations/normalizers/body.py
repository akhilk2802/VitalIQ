"""
Body Metrics Data Normalizer

Transforms body composition data from external sources into VitalIQ's BodyMetrics model.
"""
from datetime import datetime
from typing import Dict, Any

from app.models.body_metrics import BodyMetrics
from app.utils.enums import SyncDataType, DataSource
from app.integrations.normalizers.base import BaseNormalizer


class BodyNormalizer(BaseNormalizer[BodyMetrics]):
    """
    Normalizer for body metrics data from external sources.
    
    Handles data from: Withings, Fitbit (Aria), Garmin Index, etc.
    """
    
    MODEL_CLASS = BodyMetrics
    DATA_TYPE = SyncDataType.body
    TARGET_TABLE = "body_metrics"
    
    def normalize_single(self, raw_data: Dict[str, Any], source: DataSource) -> BodyMetrics:
        """
        Transform Vital body data into BodyMetrics.
        
        Vital body data format:
        {
            "id": "body_xxx",
            "calendar_date": "2024-01-15",
            "weight_kg": 75.5,
            "body_fat_percentage": 18.5,
            "bmi": 24.2,
            "lean_body_mass_kg": 61.5,
            "bone_mass_kg": 3.2,
            "muscle_mass_kg": 58.3,
            "source": {"name": "Withings", "slug": "withings"}
        }
        """
        # Parse date
        calendar_date = self.parse_date(raw_data.get("calendar_date"))
        
        # Get weight (required field)
        weight_kg = self.safe_float(raw_data.get("weight_kg"))
        if not weight_kg or weight_kg <= 0:
            # Try alternative field names
            weight_kg = self.safe_float(raw_data.get("weight"))
            if raw_data.get("weight_unit") == "lb":
                weight_kg = weight_kg * 0.453592  # Convert lbs to kg
        
        # Get body composition metrics
        body_fat_pct = self.safe_float(raw_data.get("body_fat_percentage"))
        bmi = self.safe_float(raw_data.get("bmi"))
        muscle_mass_kg = self.safe_float(raw_data.get("muscle_mass_kg"))
        
        # Get source name
        source_info = raw_data.get("source", {})
        source_name = source_info.get("slug", source.value) if isinstance(source_info, dict) else source.value
        
        return BodyMetrics(
            user_id=self.user_id,
            date=calendar_date,
            weight_kg=round(weight_kg, 1) if weight_kg else 0,
            body_fat_pct=round(body_fat_pct, 1) if body_fat_pct and body_fat_pct > 0 else None,
            bmi=round(bmi, 1) if bmi and bmi > 0 else None,
            muscle_mass_kg=round(muscle_mass_kg, 1) if muscle_mass_kg and muscle_mass_kg > 0 else None,
            source=source_name,
            external_id=raw_data.get("id"),
            synced_at=datetime.utcnow()
        )
