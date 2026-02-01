"""
Mutual Information detector for non-linear relationships.

Mutual Information measures general statistical dependency between variables,
capturing both linear and non-linear relationships that Pearson might miss.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple

from app.ml.correlation.base import BaseCorrelationDetector, CorrelationResult
from app.utils.enums import CorrelationType, CorrelationStrength


class MutualInformationDetector(BaseCorrelationDetector):
    """
    Detector for non-linear relationships using Mutual Information.
    
    MI measures how much knowing one variable reduces uncertainty about another.
    Higher MI = stronger statistical dependency (but not direction).
    """
    
    correlation_type = CorrelationType.mutual_information
    
    # Focus on outcome metrics where non-linear effects are likely
    OUTCOME_METRICS = [
        'sleep_quality', 'sleep_hours', 'awakenings',
        'resting_hr', 'hrv', 
        'blood_glucose_fasting', 'blood_glucose_post_meal',
        'weight_kg', 'body_fat_pct'
    ]
    
    PREDICTOR_METRICS = [
        'exercise_minutes', 'exercise_calories', 'exercise_intensity_avg',
        'total_calories', 'total_protein_g', 'total_carbs_g', 
        'total_sugar_g', 'total_fats_g',
        'sleep_hours', 'sleep_quality'
    ]
    
    def __init__(
        self,
        min_samples: int = 20,
        min_mi_score: float = 0.1,
        n_neighbors: int = 3
    ):
        """
        Initialize the detector.
        
        Args:
            min_samples: Minimum data points required
            min_mi_score: Minimum normalized MI to report (0-1)
            n_neighbors: Number of neighbors for MI estimation (sklearn param)
        """
        self.min_samples = min_samples
        self.min_mi_score = min_mi_score
        self.n_neighbors = n_neighbors
    
    async def detect(
        self,
        df: pd.DataFrame,
        metric_pairs: Optional[List[Tuple[str, str]]] = None
    ) -> List[CorrelationResult]:
        """
        Detect non-linear dependencies using Mutual Information.
        
        Args:
            df: DataFrame with metric columns
            metric_pairs: Optional specific pairs to test
        
        Returns:
            List of significant non-linear correlations
        """
        results = []
        
        # Generate pairs if not specified
        if metric_pairs is None:
            metric_pairs = self._generate_pairs(df.columns.tolist())
        
        for metric_a, metric_b in metric_pairs:
            if metric_a not in df.columns or metric_b not in df.columns:
                continue
            
            # Get clean data
            pair_df = df[[metric_a, metric_b]].dropna()
            
            if len(pair_df) < self.min_samples:
                continue
            
            # Compute Mutual Information
            mi_result = self._compute_mutual_information(
                pair_df[metric_a].values,
                pair_df[metric_b].values
            )
            
            if mi_result is None:
                continue
            
            mi_normalized = mi_result['mi_normalized']
            
            if mi_normalized < self.min_mi_score:
                continue
            
            # MI is always positive, so we use a different strength scale
            strength = self._mi_to_strength(mi_normalized)
            
            results.append(CorrelationResult(
                metric_a=metric_a,
                metric_b=metric_b,
                correlation_type=self.correlation_type,
                correlation_value=round(mi_normalized, 4),
                strength=strength,
                p_value=None,  # MI doesn't have a direct p-value
                is_significant=mi_normalized >= 0.15,
                lag_days=0,
                granularity="daily",
                sample_size=len(pair_df),
                confidence=round(mi_normalized, 4),
                details={
                    'mi_raw': round(mi_result['mi_raw'], 4),
                    'mi_normalized': round(mi_normalized, 4),
                    'interpretation': 'Non-linear statistical dependency detected',
                    'note': 'MI captures relationships that Pearson correlation may miss'
                }
            ))
        
        # Sort by MI score
        results.sort(key=lambda x: x.correlation_value, reverse=True)
        return results
    
    def _compute_mutual_information(
        self,
        x: np.ndarray,
        y: np.ndarray
    ) -> Optional[dict]:
        """
        Compute Mutual Information between two variables.
        
        Args:
            x: First variable values
            y: Second variable values
        
        Returns:
            Dict with mi_raw and mi_normalized, or None if computation fails
        """
        try:
            from sklearn.feature_selection import mutual_info_regression
            
            # Reshape for sklearn
            X = x.reshape(-1, 1)
            
            # Compute MI
            mi = mutual_info_regression(
                X, y,
                n_neighbors=self.n_neighbors,
                random_state=42
            )[0]
            
            # Normalize MI to roughly 0-1 range
            # Theoretical max is min(H(X), H(Y)), we approximate
            mi_normalized = min(1.0, mi / 2.0)
            
            return {
                'mi_raw': mi,
                'mi_normalized': mi_normalized
            }
            
        except Exception:
            return None
    
    def _generate_pairs(self, columns: List[str]) -> List[Tuple[str, str]]:
        """Generate meaningful predictor-outcome pairs."""
        pairs = []
        
        for predictor in self.PREDICTOR_METRICS:
            for outcome in self.OUTCOME_METRICS:
                if predictor != outcome and predictor in columns and outcome in columns:
                    pairs.append((predictor, outcome))
        
        return pairs
    
    @staticmethod
    def _mi_to_strength(mi_normalized: float) -> CorrelationStrength:
        """
        Convert normalized MI score to strength label.
        
        MI is always positive, so we only use positive strengths.
        """
        if mi_normalized >= 0.5:
            return CorrelationStrength.strong_positive
        elif mi_normalized >= 0.3:
            return CorrelationStrength.moderate_positive
        elif mi_normalized >= 0.15:
            return CorrelationStrength.weak_positive
        else:
            return CorrelationStrength.negligible
