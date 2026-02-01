import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import date
import uuid

from app.ml.detectors.base import BaseDetector, AnomalyResult
from app.utils.enums import DetectorType, Severity


class ZScoreDetector(BaseDetector):
    """
    Z-Score based anomaly detector for single-metric anomalies.
    
    Detects values that deviate significantly from the user's baseline.
    """
    
    detector_type = DetectorType.zscore
    
    # Default thresholds for different metrics
    DEFAULT_THRESHOLDS = {
        'sleep_hours': 2.5,
        'sleep_quality': 2.5,
        'total_calories': 3.0,  # Higher threshold for calories (more variable)
        'resting_hr': 2.5,
        'hrv': 2.5,
        'bp_systolic': 2.5,
        'bp_diastolic': 2.5,
        'blood_glucose_fasting': 2.5,
        'weight_kg': 2.0,  # Lower threshold for weight (changes slowly)
    }
    
    # Absolute bounds (medical ranges)
    ABSOLUTE_BOUNDS = {
        'blood_glucose_fasting': {'min': 70, 'max': 140},
        'resting_hr': {'min': 40, 'max': 100},
        'bp_systolic': {'min': 90, 'max': 140},
        'bp_diastolic': {'min': 60, 'max': 90},
        'spo2': {'min': 94, 'max': 100},
    }
    
    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
    
    async def detect(
        self,
        feature_df: pd.DataFrame,
        baselines: Dict[str, Dict[str, float]],
        source_mapping: Optional[Dict] = None,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies using Z-score method.
        
        Args:
            feature_df: DataFrame with daily feature matrix
            baselines: Dict of baseline stats per metric {metric: {mean, std, ...}}
            source_mapping: Optional mapping of (date, metric) -> (source_table, source_id)
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for metric_name, threshold in self.thresholds.items():
            if metric_name not in feature_df.columns:
                continue
            
            if metric_name not in baselines:
                continue
            
            baseline = baselines[metric_name]
            mean = baseline['mean']
            std = baseline['std']
            
            if std == 0:
                continue  # Can't calculate z-score with zero std
            
            for idx, row in feature_df.iterrows():
                value = row[metric_name]
                
                if pd.isna(value):
                    continue
                
                # Calculate Z-score
                z_score = abs((value - mean) / std)
                
                # Check if it's an anomaly
                is_zscore_anomaly = z_score > threshold
                is_bounds_anomaly = self._check_absolute_bounds(metric_name, value)
                
                if is_zscore_anomaly or is_bounds_anomaly:
                    # Calculate anomaly score (0-1)
                    anomaly_score = min(1.0, z_score / (threshold + 2))
                    
                    if is_bounds_anomaly:
                        anomaly_score = max(anomaly_score, 0.7)  # Boost score for bounds violation
                    
                    # Get source info
                    row_date = row['date'] if isinstance(row['date'], date) else row['date'].date()
                    source_table, source_id = self._get_source_info(
                        metric_name, row_date, source_mapping
                    )
                    
                    anomalies.append(AnomalyResult(
                        date=row_date,
                        source_table=source_table,
                        source_id=source_id,
                        metric_name=metric_name,
                        metric_value=float(value),
                        baseline_value=float(mean),
                        detector_type=self.detector_type,
                        severity=self.score_to_severity(anomaly_score),
                        anomaly_score=round(anomaly_score, 3),
                        details={
                            'z_score': round(z_score, 3),
                            'threshold': threshold,
                            'std': round(std, 3),
                            'bounds_violation': is_bounds_anomaly,
                        }
                    ))
        
        return anomalies
    
    def _check_absolute_bounds(self, metric_name: str, value: float) -> bool:
        """Check if value violates absolute medical bounds"""
        if metric_name not in self.ABSOLUTE_BOUNDS:
            return False
        
        bounds = self.ABSOLUTE_BOUNDS[metric_name]
        return value < bounds['min'] or value > bounds['max']
    
    def _get_source_info(
        self, 
        metric_name: str, 
        metric_date: date,
        source_mapping: Optional[Dict]
    ) -> tuple:
        """Get the source table and ID for a metric"""
        if source_mapping and (metric_date, metric_name) in source_mapping:
            return source_mapping[(metric_date, metric_name)]
        
        # Infer source table from metric name
        metric_to_table = {
            'sleep_hours': 'sleep_entries',
            'sleep_quality': 'sleep_entries',
            'awakenings': 'sleep_entries',
            'total_calories': 'food_entries',
            'total_protein_g': 'food_entries',
            'total_carbs_g': 'food_entries',
            'total_sugar_g': 'food_entries',
            'exercise_minutes': 'exercise_entries',
            'exercise_calories': 'exercise_entries',
            'resting_hr': 'vital_signs',
            'hrv': 'vital_signs',
            'bp_systolic': 'vital_signs',
            'bp_diastolic': 'vital_signs',
            'weight_kg': 'body_metrics',
            'body_fat_pct': 'body_metrics',
            'blood_glucose_fasting': 'chronic_metrics',
            'blood_glucose_post_meal': 'chronic_metrics',
        }
        
        table = metric_to_table.get(metric_name, 'unknown')
        return (table, uuid.uuid4())  # Generate placeholder UUID
