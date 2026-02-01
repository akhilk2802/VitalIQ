"""
Pearson and Spearman correlation detectors for linear/monotonic relationships.

- Pearson: Measures linear correlation (requires normal distribution)
- Spearman: Measures monotonic correlation (rank-based, more robust)
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from scipy import stats

from app.ml.correlation.base import BaseCorrelationDetector, CorrelationResult
from app.utils.enums import CorrelationType


class PearsonSpearmanDetector(BaseCorrelationDetector):
    """
    Detector for Pearson (linear) and Spearman (monotonic) correlations.
    
    Detects same-day correlations between health metrics.
    """
    
    correlation_type = CorrelationType.pearson  # Primary type
    
    def __init__(
        self,
        significance_level: float = 0.05,
        min_samples: int = 14,
        min_correlation: float = 0.2,
        include_spearman: bool = True
    ):
        """
        Initialize the detector.
        
        Args:
            significance_level: P-value threshold for significance
            min_samples: Minimum data points required
            min_correlation: Minimum |r| to report (filter weak correlations)
            include_spearman: Whether to also compute Spearman correlation
        """
        self.significance_level = significance_level
        self.min_samples = min_samples
        self.min_correlation = min_correlation
        self.include_spearman = include_spearman
    
    async def detect(
        self,
        df: pd.DataFrame,
        metric_pairs: Optional[List[Tuple[str, str]]] = None
    ) -> List[CorrelationResult]:
        """
        Detect Pearson and Spearman correlations.
        
        Args:
            df: DataFrame with metric columns
            metric_pairs: Optional specific pairs to test
        
        Returns:
            List of significant correlations
        """
        results = []
        
        # Get numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Generate all pairs if not specified
        if metric_pairs is None:
            # Test all unique pairs
            pairs = []
            for i, col_a in enumerate(numeric_cols):
                for col_b in numeric_cols[i+1:]:
                    pairs.append((col_a, col_b))
            metric_pairs = pairs
        
        for metric_a, metric_b in metric_pairs:
            if metric_a not in df.columns or metric_b not in df.columns:
                continue
            
            # Get clean data
            pair_df = df[[metric_a, metric_b]].dropna()
            
            if len(pair_df) < self.min_samples:
                continue
            
            x = pair_df[metric_a].values
            y = pair_df[metric_b].values
            
            # Pearson correlation
            pearson_r, pearson_p = stats.pearsonr(x, y)
            
            if abs(pearson_r) >= self.min_correlation:
                confidence = (1 - pearson_p) * abs(pearson_r)
                
                results.append(CorrelationResult(
                    metric_a=metric_a,
                    metric_b=metric_b,
                    correlation_type=CorrelationType.pearson,
                    correlation_value=round(pearson_r, 4),
                    strength=self.get_strength(pearson_r),
                    p_value=round(pearson_p, 6),
                    is_significant=pearson_p < self.significance_level,
                    lag_days=0,
                    granularity="daily",
                    sample_size=len(pair_df),
                    confidence=round(confidence, 4),
                    details={
                        'method': 'pearson',
                        'r_squared': round(pearson_r ** 2, 4),
                    }
                ))
            
            # Spearman correlation (if enabled and different from Pearson)
            if self.include_spearman:
                spearman_r, spearman_p = stats.spearmanr(x, y)
                
                # Only add if meaningfully different from Pearson
                if (abs(spearman_r) >= self.min_correlation and 
                    abs(spearman_r - pearson_r) > 0.1):
                    
                    confidence = (1 - spearman_p) * abs(spearman_r)
                    
                    results.append(CorrelationResult(
                        metric_a=metric_a,
                        metric_b=metric_b,
                        correlation_type=CorrelationType.spearman,
                        correlation_value=round(spearman_r, 4),
                        strength=self.get_strength(spearman_r),
                        p_value=round(spearman_p, 6),
                        is_significant=spearman_p < self.significance_level,
                        lag_days=0,
                        granularity="daily",
                        sample_size=len(pair_df),
                        confidence=round(confidence, 4),
                        details={
                            'method': 'spearman',
                            'pearson_r': round(pearson_r, 4),
                            'difference_from_pearson': round(spearman_r - pearson_r, 4),
                        }
                    ))
        
        # Sort by absolute correlation value
        results.sort(key=lambda x: abs(x.correlation_value), reverse=True)
        return results
