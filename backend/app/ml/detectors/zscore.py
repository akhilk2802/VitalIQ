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
    Supports:
    - Robust statistics (median/IQR) for outlier-resistant detection
    - Adaptive thresholds based on data variability
    - EWMA-based baselines for recent-weighted comparison
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
    
    # Metrics that should use tighter adaptive thresholds (health-critical)
    SENSITIVE_METRICS = {'bp_systolic', 'bp_diastolic', 'blood_glucose_fasting', 'resting_hr'}
    
    # Metrics that naturally have high variability (looser thresholds)
    HIGH_VARIANCE_METRICS = {'total_calories', 'exercise_minutes', 'exercise_calories', 'hrv'}
    
    def __init__(
        self, 
        thresholds: Optional[Dict[str, float]] = None,
        use_robust: bool = True,
        use_adaptive: bool = True,
        use_ewma_baseline: bool = False
    ):
        """
        Initialize the Z-Score detector.
        
        Args:
            thresholds: Custom thresholds per metric (overrides defaults)
            use_robust: Use median/IQR instead of mean/std (resistant to outliers)
            use_adaptive: Dynamically adjust thresholds based on data characteristics
            use_ewma_baseline: Use EWMA baseline instead of mean (recent-weighted)
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.use_robust = use_robust
        self.use_adaptive = use_adaptive
        self.use_ewma_baseline = use_ewma_baseline
    
    async def detect(
        self,
        feature_df: pd.DataFrame,
        baselines: Dict[str, Dict[str, float]],
        source_mapping: Optional[Dict] = None,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies using Z-score method with robust statistics and adaptive thresholds.
        
        Args:
            feature_df: DataFrame with daily feature matrix
            baselines: Dict of baseline stats per metric {metric: {mean, std, median, iqr, ewma, ...}}
            source_mapping: Optional mapping of (date, metric) -> (source_table, source_id)
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for metric_name, base_threshold in self.thresholds.items():
            if metric_name not in feature_df.columns:
                continue
            
            if metric_name not in baselines:
                continue
            
            baseline = baselines[metric_name]
            
            # Choose center and spread based on settings
            if self.use_robust and 'median' in baseline and 'robust_std' in baseline:
                # Robust: Use median and MAD-based std (resistant to outliers)
                if self.use_ewma_baseline and 'ewma' in baseline:
                    center = baseline['ewma']  # Recent-weighted center
                else:
                    center = baseline['median']
                spread = baseline['robust_std']
            else:
                # Traditional: Use mean and std
                if self.use_ewma_baseline and 'ewma' in baseline:
                    center = baseline['ewma']
                else:
                    center = baseline['mean']
                spread = baseline['std']
            
            if spread == 0:
                continue  # Can't calculate z-score with zero spread
            
            # Calculate adaptive threshold
            threshold = self._get_adaptive_threshold(metric_name, baseline, base_threshold)
            
            for idx, row in feature_df.iterrows():
                value = row[metric_name]
                
                if pd.isna(value):
                    continue
                
                # Calculate Modified Z-score (robust version)
                z_score = abs((value - center) / spread)
                
                # Also check IQR-based outlier detection (Tukey's fences)
                is_iqr_outlier = False
                if self.use_robust and 'q1' in baseline and 'q3' in baseline:
                    iqr = baseline['iqr']
                    if iqr > 0:
                        # Tukey's fences: outlier if outside Q1-1.5*IQR or Q3+1.5*IQR
                        lower_fence = baseline['q1'] - 1.5 * iqr
                        upper_fence = baseline['q3'] + 1.5 * iqr
                        is_iqr_outlier = value < lower_fence or value > upper_fence
                
                # Check if it's an anomaly
                is_zscore_anomaly = z_score > threshold
                is_bounds_anomaly = self._check_absolute_bounds(metric_name, value)
                
                # Require either Z-score OR (IQR outlier + bounds) to flag
                if is_zscore_anomaly or is_bounds_anomaly or (is_iqr_outlier and is_bounds_anomaly):
                    # Calculate anomaly score (0-1)
                    anomaly_score = min(1.0, z_score / (threshold + 2))
                    
                    if is_bounds_anomaly:
                        anomaly_score = max(anomaly_score, 0.7)  # Boost score for bounds violation
                    
                    if is_iqr_outlier:
                        anomaly_score = max(anomaly_score, 0.5)  # Boost for IQR outlier
                    
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
                        baseline_value=float(center),
                        detector_type=self.detector_type,
                        severity=self.score_to_severity(anomaly_score),
                        anomaly_score=round(anomaly_score, 3),
                        details={
                            'z_score': round(z_score, 3),
                            'threshold': round(threshold, 3),
                            'spread': round(spread, 3),
                            'center_type': 'ewma' if self.use_ewma_baseline else ('median' if self.use_robust else 'mean'),
                            'bounds_violation': is_bounds_anomaly,
                            'iqr_outlier': is_iqr_outlier,
                            'adaptive_threshold': self.use_adaptive,
                        }
                    ))
        
        return anomalies
    
    def _get_adaptive_threshold(
        self, 
        metric_name: str, 
        baseline: Dict[str, float],
        base_threshold: float
    ) -> float:
        """
        Calculate adaptive threshold based on data characteristics.
        
        Adapts based on:
        - Coefficient of variation (CV): Higher CV → higher threshold
        - Sample size: Fewer samples → higher threshold (less confidence)
        - Metric sensitivity: Health-critical metrics get tighter bounds
        
        Args:
            metric_name: Name of the metric
            baseline: Baseline statistics including std, mean, n_samples
            base_threshold: The default threshold for this metric
        
        Returns:
            Adjusted threshold value
        """
        if not self.use_adaptive:
            return base_threshold
        
        threshold = base_threshold
        
        # Factor 1: Coefficient of Variation (CV)
        # High CV indicates naturally variable data → need higher threshold
        mean = baseline.get('mean', 1)
        std = baseline.get('std', 0)
        if mean != 0 and std > 0:
            cv = std / abs(mean)
            if cv > 0.3:  # High variability
                threshold *= 1.2
            elif cv > 0.5:  # Very high variability
                threshold *= 1.4
            elif cv < 0.1:  # Low variability (stable metric)
                threshold *= 0.9
        
        # Factor 2: Sample size adjustment
        # Fewer samples → less confident in baseline → higher threshold
        n_samples = baseline.get('n_samples', 30)
        if n_samples < 7:
            threshold *= 1.5  # Very few samples, be conservative
        elif n_samples < 14:
            threshold *= 1.2  # Still building baseline
        
        # Factor 3: Metric sensitivity
        if metric_name in self.SENSITIVE_METRICS:
            # Health-critical: tighter threshold (catch more anomalies)
            threshold *= 0.85
        elif metric_name in self.HIGH_VARIANCE_METRICS:
            # Naturally variable: looser threshold (fewer false positives)
            threshold *= 1.15
        
        # Ensure threshold stays within reasonable bounds
        return max(1.5, min(threshold, 5.0))
    
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
