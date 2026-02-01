import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from datetime import date
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import uuid

from app.ml.detectors.base import BaseDetector, AnomalyResult
from app.utils.enums import DetectorType, Severity


class IsolationForestDetector(BaseDetector):
    """
    Isolation Forest based anomaly detector for multivariate anomalies.
    
    Detects unusual combinations of metrics that might not be anomalous individually.
    """
    
    detector_type = DetectorType.isolation_forest
    
    # Features to use for multivariate analysis
    DEFAULT_FEATURES = [
        'sleep_hours',
        'sleep_quality',
        'total_calories',
        'total_protein_g',
        'total_sugar_g',
        'exercise_minutes',
        'resting_hr',
        'hrv',
        'bp_systolic',
        'blood_glucose_fasting',
    ]
    
    def __init__(
        self,
        features: Optional[List[str]] = None,
        contamination: float = 0.05,
        n_estimators: int = 100,
        random_state: int = 42
    ):
        self.features = features or self.DEFAULT_FEATURES
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        
        self.model = None
        self.scaler = StandardScaler()
    
    async def detect(
        self,
        feature_df: pd.DataFrame,
        baselines: Dict[str, Dict[str, float]],
        source_mapping: Optional[Dict] = None,
    ) -> List[AnomalyResult]:
        """
        Detect anomalies using Isolation Forest.
        
        Args:
            feature_df: DataFrame with daily feature matrix
            baselines: Dict of baseline stats per metric (for context)
            source_mapping: Optional mapping of (date, metric) -> (source_table, source_id)
        
        Returns:
            List of detected anomalies
        """
        # Select available features
        available_features = [f for f in self.features if f in feature_df.columns]
        
        if len(available_features) < 3:
            return []  # Need at least 3 features for meaningful multivariate analysis
        
        # Prepare data
        df = feature_df.copy()
        
        # Fill missing values with column medians
        X = df[available_features].copy()
        X = X.fillna(X.median())
        
        # Drop rows that still have NaN (edge case)
        valid_mask = ~X.isna().any(axis=1)
        X = X[valid_mask]
        df = df[valid_mask]
        
        if len(X) < 10:
            return []  # Need minimum data points
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit and predict
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1
        )
        
        # Predictions: -1 for anomalies, 1 for normal
        predictions = self.model.fit_predict(X_scaled)
        
        # Get anomaly scores (more negative = more anomalous)
        scores = self.model.decision_function(X_scaled)
        
        # Normalize scores to 0-1 range (0 = normal, 1 = very anomalous)
        score_min, score_max = scores.min(), scores.max()
        if score_max > score_min:
            normalized_scores = 1 - (scores - score_min) / (score_max - score_min)
        else:
            normalized_scores = np.zeros_like(scores)
        
        # Collect anomalies
        anomalies = []
        
        for i, (pred, norm_score) in enumerate(zip(predictions, normalized_scores)):
            if pred == -1:  # Anomaly detected
                row = df.iloc[i]
                row_date = row['date'] if isinstance(row['date'], date) else row['date'].date()
                
                # Find which features contributed most to the anomaly
                feature_contributions = self._get_feature_contributions(
                    X.iloc[i], 
                    available_features, 
                    baselines
                )
                
                # Primary anomaly metric (most deviant)
                if feature_contributions:
                    primary_metric = max(feature_contributions, key=lambda x: x['deviation'])
                else:
                    primary_metric = {'name': 'multivariate', 'value': 0, 'deviation': norm_score}
                
                source_table, source_id = self._get_source_info(
                    primary_metric['name'], row_date, source_mapping
                )
                
                anomalies.append(AnomalyResult(
                    date=row_date,
                    source_table=source_table,
                    source_id=source_id,
                    metric_name='multivariate_anomaly',
                    metric_value=primary_metric.get('value', 0),
                    baseline_value=0,  # Not applicable for multivariate
                    detector_type=self.detector_type,
                    severity=self.score_to_severity(norm_score),
                    anomaly_score=round(float(norm_score), 3),
                    details={
                        'primary_metric': primary_metric['name'],
                        'feature_contributions': feature_contributions[:5],  # Top 5
                        'features_used': available_features,
                        'isolation_score': round(float(scores[i]), 3),
                    }
                ))
        
        return anomalies
    
    def _get_feature_contributions(
        self,
        row: pd.Series,
        features: List[str],
        baselines: Dict[str, Dict[str, float]]
    ) -> List[Dict]:
        """Calculate how much each feature contributed to the anomaly"""
        contributions = []
        
        for feature in features:
            if feature not in baselines:
                continue
            
            value = row[feature]
            baseline = baselines[feature]
            mean = baseline['mean']
            std = baseline['std']
            
            if std > 0:
                deviation = abs((value - mean) / std)
            else:
                deviation = 0
            
            contributions.append({
                'name': feature,
                'value': float(value),
                'baseline': float(mean),
                'deviation': round(float(deviation), 3),
            })
        
        # Sort by deviation (highest first)
        contributions.sort(key=lambda x: x['deviation'], reverse=True)
        return contributions
    
    def _get_source_info(
        self,
        metric_name: str,
        metric_date: date,
        source_mapping: Optional[Dict]
    ) -> tuple:
        """Get the source table and ID for a metric"""
        if source_mapping and (metric_date, metric_name) in source_mapping:
            return source_mapping[(metric_date, metric_name)]
        
        # For multivariate anomalies, use a generic source
        return ('multivariate', uuid.uuid4())
