"""
Cross-correlation detector for time-lagged relationships.

Finds correlations where one metric affects another with a delay.
For example: "Exercise today correlates with better sleep tomorrow."
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from scipy import stats

from app.ml.correlation.base import BaseCorrelationDetector, CorrelationResult
from app.utils.enums import CorrelationType


class CrossCorrelationDetector(BaseCorrelationDetector):
    """
    Detector for time-lagged cross-correlations.
    
    Tests if metric A at time t correlates with metric B at time t+lag.
    """
    
    correlation_type = CorrelationType.cross_correlation
    
    # Pre-defined pairs that are likely to have time-lagged effects
    DEFAULT_LAG_PAIRS = [
        # Exercise effects
        ('exercise_minutes', 'sleep_quality'),
        ('exercise_minutes', 'sleep_hours'),
        ('exercise_minutes', 'resting_hr'),
        ('exercise_minutes', 'hrv'),
        ('exercise_calories', 'weight_kg'),
        
        # Nutrition effects
        ('total_sugar_g', 'sleep_quality'),
        ('total_calories', 'weight_kg'),
        ('total_carbs_g', 'blood_glucose_fasting'),
        ('total_protein_g', 'exercise_calories'),
        
        # Sleep effects
        ('sleep_hours', 'hrv'),
        ('sleep_quality', 'resting_hr'),
        ('sleep_hours', 'exercise_minutes'),
        ('awakenings', 'resting_hr'),
    ]
    
    def __init__(
        self,
        max_lag: int = 3,
        significance_level: float = 0.05,
        min_samples: int = 14,
        min_correlation: float = 0.25
    ):
        """
        Initialize the detector.
        
        Args:
            max_lag: Maximum lag days to test (1 to max_lag)
            significance_level: P-value threshold for significance
            min_samples: Minimum data points required after lag shift
            min_correlation: Minimum |r| to report
        """
        self.max_lag = max_lag
        self.significance_level = significance_level
        self.min_samples = min_samples
        self.min_correlation = min_correlation
    
    async def detect(
        self,
        df: pd.DataFrame,
        metric_pairs: Optional[List[Tuple[str, str]]] = None
    ) -> List[CorrelationResult]:
        """
        Detect time-lagged correlations.
        
        Args:
            df: DataFrame with metric columns (must be sorted by date)
            metric_pairs: Optional specific pairs to test
        
        Returns:
            List of significant time-lagged correlations
        """
        results = []
        
        # Use default pairs if not specified
        if metric_pairs is None:
            metric_pairs = self.DEFAULT_LAG_PAIRS
        
        for metric_a, metric_b in metric_pairs:
            if metric_a not in df.columns or metric_b not in df.columns:
                continue
            
            # Find best lag
            best_result = None
            best_abs_corr = 0
            
            for lag in range(1, self.max_lag + 1):
                result = self._compute_lagged_correlation(
                    df, metric_a, metric_b, lag
                )
                
                if result and abs(result['correlation']) > best_abs_corr:
                    if result['is_significant']:
                        best_result = result
                        best_abs_corr = abs(result['correlation'])
            
            if best_result:
                r = best_result['correlation']
                confidence = (1 - best_result['p_value']) * abs(r)
                
                results.append(CorrelationResult(
                    metric_a=metric_a,
                    metric_b=metric_b,
                    correlation_type=self.correlation_type,
                    correlation_value=round(r, 4),
                    strength=self.get_strength(r),
                    p_value=round(best_result['p_value'], 6),
                    is_significant=True,
                    lag_days=best_result['lag'],
                    granularity="daily",
                    sample_size=best_result['sample_size'],
                    confidence=round(confidence, 4),
                    details={
                        'interpretation': f"{metric_a} at day t affects {metric_b} at day t+{best_result['lag']}",
                        'all_lags_tested': self.max_lag,
                        'optimal_lag': best_result['lag'],
                    }
                ))
        
        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def _compute_lagged_correlation(
        self,
        df: pd.DataFrame,
        metric_a: str,
        metric_b: str,
        lag: int
    ) -> Optional[dict]:
        """
        Compute correlation between metric_a[t] and metric_b[t+lag].
        
        Args:
            df: DataFrame with metrics
            metric_a: The leading/cause metric
            metric_b: The lagging/effect metric
            lag: Number of days to lag metric_b
        
        Returns:
            Dict with correlation, p_value, lag, sample_size if valid
        """
        try:
            # Shift metric_a back (or equivalently, compare a[:-lag] with b[lag:])
            a_values = df[metric_a].iloc[:-lag].values
            b_values = df[metric_b].iloc[lag:].values
            
            # Create paired DataFrame and drop NaN
            pair_df = pd.DataFrame({'a': a_values, 'b': b_values}).dropna()
            
            if len(pair_df) < self.min_samples:
                return None
            
            # Compute Pearson correlation
            r, p = stats.pearsonr(pair_df['a'], pair_df['b'])
            
            if abs(r) < self.min_correlation:
                return None
            
            return {
                'correlation': r,
                'p_value': p,
                'lag': lag,
                'sample_size': len(pair_df),
                'is_significant': p < self.significance_level
            }
            
        except Exception:
            return None
