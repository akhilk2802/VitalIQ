"""
Sleep Data Normalizer

Transforms sleep data from external sources (Vital API format) 
into VitalIQ's SleepEntry model.
"""
from datetime import datetime
from typing import Dict, Any

from app.models.sleep_entry import SleepEntry
from app.utils.enums import SyncDataType, DataSource
from app.integrations.normalizers.base import BaseNormalizer


class SleepNormalizer(BaseNormalizer[SleepEntry]):
    """
    Normalizer for sleep data from external sources.
    
    Handles data from: Fitbit, Oura, Garmin, Withings, Whoop
    """
    
    MODEL_CLASS = SleepEntry
    DATA_TYPE = SyncDataType.sleep
    TARGET_TABLE = "sleep_entries"
    
    def normalize_single(self, raw_data: Dict[str, Any], source: DataSource) -> SleepEntry:
        """
        Transform Vital sleep data into SleepEntry.
        
        Vital sleep data format:
        {
            "id": "sleep_xxx",
            "calendar_date": "2024-01-15",
            "bedtime_start": "2024-01-14T22:30:00+00:00",
            "bedtime_stop": "2024-01-15T06:45:00+00:00",
            "duration_in_bed": 29700,  # seconds
            "duration_asleep": 27000,  # seconds
            "sleep_efficiency": 0.91,
            "deep_sleep_duration": 5400,  # seconds
            "rem_sleep_duration": 7200,  # seconds
            "light_sleep_duration": 14400,  # seconds
            "awake_duration": 2700,  # seconds
            "wake_up_count": 2,
            "source": {"name": "Fitbit", "slug": "fitbit"}
        }
        """
        # Parse times
        calendar_date = self.parse_date(raw_data.get("calendar_date"))
        bedtime = self.parse_datetime(raw_data.get("bedtime_start"))
        wake_time = self.parse_datetime(raw_data.get("bedtime_stop"))
        
        # Calculate duration in hours from seconds
        duration_seconds = self.safe_int(raw_data.get("duration_in_bed", 0))
        duration_hours = round(duration_seconds / 3600, 2)
        
        # Calculate quality score (0-100) from efficiency and other factors
        quality_score = self._calculate_quality_score(raw_data)
        
        # Convert sleep stage durations from seconds to minutes
        deep_sleep_mins = self.safe_int(raw_data.get("deep_sleep_duration", 0)) // 60
        rem_sleep_mins = self.safe_int(raw_data.get("rem_sleep_duration", 0)) // 60
        awakenings = self.safe_int(raw_data.get("wake_up_count", 0))
        
        # Get source name
        source_info = raw_data.get("source", {})
        source_name = source_info.get("slug", source.value) if isinstance(source_info, dict) else source.value
        
        return SleepEntry(
            user_id=self.user_id,
            date=calendar_date,
            bedtime=bedtime,
            wake_time=wake_time,
            duration_hours=duration_hours,
            quality_score=quality_score,
            deep_sleep_minutes=deep_sleep_mins if deep_sleep_mins > 0 else None,
            rem_sleep_minutes=rem_sleep_mins if rem_sleep_mins > 0 else None,
            awakenings=awakenings if awakenings > 0 else None,
            source=source_name,
            external_id=raw_data.get("id"),
            synced_at=datetime.utcnow()
        )
    
    def _calculate_quality_score(self, raw_data: Dict[str, Any]) -> int:
        """
        Calculate a sleep quality score (0-100) from available metrics.
        
        Factors:
        - Sleep efficiency (main factor)
        - Deep sleep percentage
        - REM sleep percentage
        - Number of awakenings
        """
        # Base score from efficiency (if available)
        efficiency = self.safe_float(raw_data.get("sleep_efficiency"), 0.8)
        base_score = efficiency * 100
        
        # Adjust for sleep composition
        duration_asleep = self.safe_int(raw_data.get("duration_asleep", 0))
        if duration_asleep > 0:
            deep_pct = self.safe_int(raw_data.get("deep_sleep_duration", 0)) / duration_asleep
            rem_pct = self.safe_int(raw_data.get("rem_sleep_duration", 0)) / duration_asleep
            
            # Ideal: 15-25% deep, 20-25% REM
            if 0.15 <= deep_pct <= 0.25:
                base_score += 5
            if 0.20 <= rem_pct <= 0.25:
                base_score += 5
        
        # Penalize for too many awakenings
        awakenings = self.safe_int(raw_data.get("wake_up_count", 0))
        if awakenings > 5:
            base_score -= 10
        elif awakenings > 2:
            base_score -= 5
        
        # Clamp to 0-100
        return max(0, min(100, int(base_score)))
