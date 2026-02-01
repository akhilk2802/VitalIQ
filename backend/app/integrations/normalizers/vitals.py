"""
Vital Signs Data Normalizer

Transforms vital signs data (heart rate, HRV, SpO2, etc.) from external sources 
into VitalIQ's VitalSigns model.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.models.vital_signs import VitalSigns
from app.utils.enums import SyncDataType, DataSource, TimeOfDay
from app.integrations.normalizers.base import BaseNormalizer


class VitalsNormalizer(BaseNormalizer[VitalSigns]):
    """
    Normalizer for vital signs data from external sources.
    
    Handles data from: Fitbit, Oura, Garmin, Whoop, Apple Health (via Vital)
    
    Note: Vital returns vitals as time series data. We aggregate to daily summaries.
    """
    
    MODEL_CLASS = VitalSigns
    DATA_TYPE = SyncDataType.vitals
    TARGET_TABLE = "vital_signs"
    
    def normalize_single(self, raw_data: Dict[str, Any], source: DataSource) -> VitalSigns:
        """
        Transform Vital vital signs data into VitalSigns.
        
        This handles the aggregated format after we've combined time series data.
        
        Expected aggregated format:
        {
            "id": "vitals_xxx",
            "calendar_date": "2024-01-15",
            "resting_hr": 62,
            "hrv_ms": 45,
            "spo2": 98,
            "time_of_day": "morning",
            "source": {"name": "Fitbit", "slug": "fitbit"}
        }
        """
        # Parse date
        calendar_date = self.parse_date(raw_data.get("calendar_date"))
        
        # Get time of day (default to morning for resting measurements)
        time_str = raw_data.get("time_of_day", "morning")
        time_of_day = self._map_time_of_day(time_str)
        
        # Get vital measurements
        resting_hr = self.safe_int(raw_data.get("resting_hr"))
        hrv_ms = self.safe_int(raw_data.get("hrv_ms") or raw_data.get("hrv"))
        spo2 = self.safe_int(raw_data.get("spo2") or raw_data.get("blood_oxygen"))
        
        # Blood pressure (if available)
        bp_systolic = self.safe_int(raw_data.get("bp_systolic"))
        bp_diastolic = self.safe_int(raw_data.get("bp_diastolic"))
        
        # Respiratory rate (if available)
        resp_rate = self.safe_int(raw_data.get("respiratory_rate"))
        
        # Body temperature (if available)
        body_temp = self.safe_float(raw_data.get("body_temperature"))
        
        # Get source name
        source_info = raw_data.get("source", {})
        source_name = source_info.get("slug", source.value) if isinstance(source_info, dict) else source.value
        
        return VitalSigns(
            user_id=self.user_id,
            date=calendar_date,
            time_of_day=time_of_day,
            resting_heart_rate=resting_hr if resting_hr > 0 else None,
            hrv_ms=hrv_ms if hrv_ms > 0 else None,
            spo2=spo2 if spo2 > 0 else None,
            blood_pressure_systolic=bp_systolic if bp_systolic > 0 else None,
            blood_pressure_diastolic=bp_diastolic if bp_diastolic > 0 else None,
            respiratory_rate=resp_rate if resp_rate > 0 else None,
            body_temperature=body_temp if body_temp and body_temp > 0 else None,
            source=source_name,
            external_id=raw_data.get("id"),
            synced_at=datetime.utcnow()
        )
    
    @staticmethod
    def aggregate_time_series(
        heartrate_data: List[Dict],
        hrv_data: List[Dict],
        spo2_data: List[Dict],
        calendar_date: str
    ) -> Dict[str, Any]:
        """
        Aggregate time series vital signs data into a single daily record.
        
        Takes raw time series from Vital API and creates a summarized record
        suitable for our normalize_single method.
        
        Args:
            heartrate_data: List of heart rate readings
            hrv_data: List of HRV readings
            spo2_data: List of SpO2 readings
            calendar_date: The date to aggregate for
            
        Returns:
            Aggregated dict ready for normalize_single
        """
        import uuid
        
        result = {
            "id": f"vitals_{uuid.uuid4().hex[:12]}",
            "calendar_date": calendar_date,
            "time_of_day": "morning",
        }
        
        # Get resting heart rate (lowest or labeled as "resting")
        if heartrate_data:
            resting_readings = [
                d["value"] for d in heartrate_data 
                if d.get("type") == "resting" or d.get("value", 200) < 80
            ]
            if resting_readings:
                result["resting_hr"] = min(resting_readings)
            elif heartrate_data:
                # Fall back to minimum value
                result["resting_hr"] = min(d.get("value", 0) for d in heartrate_data)
            
            # Get source from first reading
            if heartrate_data[0].get("source"):
                result["source"] = heartrate_data[0]["source"]
        
        # Get HRV (typically morning reading is most meaningful)
        if hrv_data:
            # Take the first reading of the day (usually morning)
            result["hrv_ms"] = hrv_data[0].get("value")
            if not result.get("source") and hrv_data[0].get("source"):
                result["source"] = hrv_data[0]["source"]
        
        # Get SpO2 (average or last reading)
        if spo2_data:
            values = [d.get("value", 0) for d in spo2_data if d.get("value")]
            if values:
                result["spo2"] = round(sum(values) / len(values))
            if not result.get("source") and spo2_data[0].get("source"):
                result["source"] = spo2_data[0]["source"]
        
        return result
    
    def _map_time_of_day(self, time_str: str) -> TimeOfDay:
        """Map string to TimeOfDay enum."""
        time_map = {
            "morning": TimeOfDay.morning,
            "am": TimeOfDay.morning,
            "afternoon": TimeOfDay.afternoon,
            "pm": TimeOfDay.afternoon,
            "evening": TimeOfDay.evening,
            "night": TimeOfDay.night,
        }
        return time_map.get(time_str.lower(), TimeOfDay.morning)
