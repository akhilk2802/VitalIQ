"""
Activity/Exercise Data Normalizer

Transforms activity and workout data from external sources into VitalIQ's ExerciseEntry model.
"""
from datetime import datetime
from typing import Dict, Any

from app.models.exercise_entry import ExerciseEntry
from app.utils.enums import SyncDataType, DataSource, ExerciseType, ExerciseIntensity
from app.integrations.normalizers.base import BaseNormalizer


class ActivityNormalizer(BaseNormalizer[ExerciseEntry]):
    """
    Normalizer for activity/workout data from external sources.
    
    Handles data from: Fitbit, Garmin, Strava, Google Fit, Whoop
    """
    
    MODEL_CLASS = ExerciseEntry
    DATA_TYPE = SyncDataType.workout
    TARGET_TABLE = "exercise_entries"
    
    # Map external sport types to our ExerciseType enum
    SPORT_TYPE_MAP = {
        # Cardio
        "running": ExerciseType.cardio,
        "run": ExerciseType.cardio,
        "jogging": ExerciseType.cardio,
        "cycling": ExerciseType.cardio,
        "bike": ExerciseType.cardio,
        "swimming": ExerciseType.cardio,
        "swim": ExerciseType.cardio,
        "walking": ExerciseType.cardio,
        "walk": ExerciseType.cardio,
        "hiking": ExerciseType.cardio,
        "rowing": ExerciseType.cardio,
        "elliptical": ExerciseType.cardio,
        "stair_climbing": ExerciseType.cardio,
        "aerobics": ExerciseType.cardio,
        "spinning": ExerciseType.cardio,
        
        # Strength
        "strength_training": ExerciseType.strength,
        "weight_training": ExerciseType.strength,
        "weights": ExerciseType.strength,
        "crossfit": ExerciseType.strength,
        "bodyweight": ExerciseType.strength,
        "functional_training": ExerciseType.strength,
        
        # Flexibility
        "yoga": ExerciseType.flexibility,
        "pilates": ExerciseType.flexibility,
        "stretching": ExerciseType.flexibility,
        "meditation": ExerciseType.flexibility,
        
        # Sports
        "tennis": ExerciseType.sports,
        "basketball": ExerciseType.sports,
        "soccer": ExerciseType.sports,
        "football": ExerciseType.sports,
        "golf": ExerciseType.sports,
        "volleyball": ExerciseType.sports,
        "badminton": ExerciseType.sports,
        "squash": ExerciseType.sports,
        "racquetball": ExerciseType.sports,
        "martial_arts": ExerciseType.sports,
        "boxing": ExerciseType.sports,
        "skiing": ExerciseType.sports,
        "snowboarding": ExerciseType.sports,
        "surfing": ExerciseType.sports,
    }
    
    def normalize_single(self, raw_data: Dict[str, Any], source: DataSource) -> ExerciseEntry:
        """
        Transform Vital workout data into ExerciseEntry.
        
        Vital workout data format:
        {
            "id": "workout_xxx",
            "calendar_date": "2024-01-15",
            "title": "Morning Run",
            "sport": "running",
            "start_time": "2024-01-15T07:00:00+00:00",
            "end_time": "2024-01-15T07:45:00+00:00",
            "duration_seconds": 2700,
            "calories": 350,
            "distance_meters": 5200,
            "average_hr": 145,
            "max_hr": 172,
            "source": {"name": "Strava", "slug": "strava"}
        }
        """
        # Parse date
        calendar_date = self.parse_date(raw_data.get("calendar_date"))
        
        # Map sport type
        sport = raw_data.get("sport", "other")
        exercise_type = self._map_sport_type(sport)
        
        # Get exercise name
        exercise_name = raw_data.get("title") or sport.replace("_", " ").title()
        
        # Calculate duration in minutes
        duration_seconds = self.safe_int(raw_data.get("duration_seconds", 0))
        duration_minutes = duration_seconds // 60
        
        # Get heart rate data
        avg_hr = self.safe_int(raw_data.get("average_hr"))
        max_hr = self.safe_int(raw_data.get("max_hr"))
        
        # Determine intensity from heart rate or default
        intensity = self._determine_intensity(avg_hr, max_hr)
        
        # Get calories
        calories = self.safe_int(raw_data.get("calories"))
        
        # Get distance in km (from meters)
        distance_meters = self.safe_float(raw_data.get("distance_meters"))
        distance_km = round(distance_meters / 1000, 2) if distance_meters else None
        
        # Get source name
        source_info = raw_data.get("source", {})
        source_name = source_info.get("slug", source.value) if isinstance(source_info, dict) else source.value
        
        return ExerciseEntry(
            user_id=self.user_id,
            date=calendar_date,
            exercise_type=exercise_type,
            exercise_name=exercise_name,
            duration_minutes=max(1, duration_minutes),  # At least 1 minute
            intensity=intensity,
            calories_burned=calories if calories > 0 else None,
            heart_rate_avg=avg_hr if avg_hr > 0 else None,
            heart_rate_max=max_hr if max_hr > 0 else None,
            distance_km=distance_km if distance_km and distance_km > 0 else None,
            source=source_name,
            external_id=raw_data.get("id"),
            synced_at=datetime.utcnow()
        )
    
    def _map_sport_type(self, sport: str) -> ExerciseType:
        """Map external sport type to our ExerciseType enum."""
        sport_lower = sport.lower().replace(" ", "_")
        return self.SPORT_TYPE_MAP.get(sport_lower, ExerciseType.other)
    
    def _determine_intensity(self, avg_hr: int, max_hr: int) -> ExerciseIntensity:
        """
        Determine exercise intensity based on heart rate.
        
        Uses average HR zones (assuming max HR ~190):
        - Low: < 110 bpm
        - Moderate: 110-140 bpm
        - High: 140-170 bpm
        - Very High: > 170 bpm
        """
        if not avg_hr:
            return ExerciseIntensity.moderate  # Default
        
        if avg_hr < 110:
            return ExerciseIntensity.low
        elif avg_hr < 140:
            return ExerciseIntensity.moderate
        elif avg_hr < 170:
            return ExerciseIntensity.high
        else:
            return ExerciseIntensity.very_high
