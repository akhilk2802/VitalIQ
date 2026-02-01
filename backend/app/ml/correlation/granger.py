"""
Granger Causality detector for finding predictive relationships.

Granger Causality tests whether one time series can help forecast another.
X "Granger-causes" Y if past values of X help predict future values of Y,
beyond what past values of Y alone can predict.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import warnings

from app.ml.correlation.base import BaseCorrelationDetector, CorrelationResult
from app.utils.enums import CorrelationType, CausalDirection


class GrangerCausalityDetector(BaseCorrelationDetector):
    """
    Granger Causality detector to find if one metric predicts another.
    
    Key features:
    - Tests both directions (X→Y and Y→X)
    - Handles non-stationary data via differencing
    - Returns causal direction and statistical significance
    """
    
    correlation_type = CorrelationType.granger_causality
    
    def __init__(
        self, 
        max_lag: int = 3,
        significance_level: float = 0.05,
        min_samples: int = 20
    ):
        """
        Initialize the Granger Causality detector.
        
        Args:
            max_lag: Maximum number of lag days to test (1-3 recommended)
            significance_level: P-value threshold for significance (default 0.05)
            min_samples: Minimum data points required for analysis
        """
        self.max_lag = max_lag
        self.significance_level = significance_level
        self.min_samples = min_samples
    
    async def detect(
        self,
        df: pd.DataFrame,
        metric_pairs: Optional[List[Tuple[str, str]]] = None
    ) -> List[CorrelationResult]:
        """
        Detect Granger causality between metric pairs.
        
        Args:
            df: DataFrame with date column and metric columns
            metric_pairs: Optional list of (metric_a, metric_b) pairs to test.
                         If None, tests all meaningful pairs.
        
        Returns:
            List of CorrelationResult for significant causal relationships
        """
        results = []
        
        # Get numeric columns (excluding date)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Generate pairs if not provided
        if metric_pairs is None:
            metric_pairs = self.get_meaningful_pairs(numeric_cols)
        
        for metric_a, metric_b in metric_pairs:
            if metric_a not in df.columns or metric_b not in df.columns:
                continue
            
            # Get clean data for both metrics
            pair_df = df[[metric_a, metric_b]].dropna()
            
            if len(pair_df) < self.min_samples:
                continue
            
            # Test both directions
            result_ab = self._test_granger(pair_df, metric_a, metric_b)
            result_ba = self._test_granger(pair_df, metric_b, metric_a)
            
            # Determine causal direction
            causal_direction = self._determine_direction(result_ab, result_ba)
            
            if causal_direction != CausalDirection.none:
                # Use the more significant result for the output
                if result_ab and (not result_ba or result_ab['p_value'] < result_ba['p_value']):
                    best_result = result_ab
                elif result_ba:
                    best_result = result_ba
                else:
                    continue
                
                # Calculate confidence (1 - p_value, capped)
                confidence = min(0.99, 1 - best_result['p_value'])
                
                results.append(CorrelationResult(
                    metric_a=metric_a,
                    metric_b=metric_b,
                    correlation_type=self.correlation_type,
                    correlation_value=round(confidence, 4),
                    strength=self.get_strength(confidence),
                    p_value=round(best_result['p_value'], 6),
                    is_significant=True,
                    lag_days=best_result['best_lag'],
                    granularity="daily",
                    sample_size=len(pair_df),
                    causal_direction=causal_direction,
                    granger_f_stat=round(best_result['f_stat'], 4),
                    confidence=round(confidence, 4),
                    details={
                        'direction': causal_direction.value,
                        'f_statistic': round(best_result['f_stat'], 4),
                        'optimal_lag': best_result['best_lag'],
                        'a_causes_b': result_ab is not None,
                        'b_causes_a': result_ba is not None,
                    }
                ))
        
        # Sort by confidence descending
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results
    
    def _test_granger(
        self, 
        df: pd.DataFrame, 
        cause_col: str, 
        effect_col: str
    ) -> Optional[Dict]:
        """
        Test if cause_col Granger-causes effect_col.
        
        Args:
            df: DataFrame with both columns
            cause_col: The potential cause variable
            effect_col: The potential effect variable
        
        Returns:
            Dict with best_lag, p_value, f_stat if significant, else None
        """
        try:
            # Import here to avoid issues if statsmodels not installed
            from statsmodels.tsa.stattools import grangercausalitytests, adfuller
            
            # Prepare data: [effect, cause] for grangercausalitytests
            data = df[[effect_col, cause_col]].copy()
            
            # Check stationarity and difference if needed
            effect_stationary = self._is_stationary(data[effect_col])
            cause_stationary = self._is_stationary(data[cause_col])
            
            if not effect_stationary:
                data[effect_col] = data[effect_col].diff()
            if not cause_stationary:
                data[cause_col] = data[cause_col].diff()
            
            # Drop NaN from differencing
            data = data.dropna()
            
            if len(data) < self.min_samples:
                return None
            
            # Run Granger test
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                test_result = grangercausalitytests(
                    data.values, 
                    maxlag=self.max_lag, 
                    verbose=False
                )
            
            # Find best lag (lowest p-value)
            best_lag = 1
            best_p = 1.0
            best_f = 0.0
            
            for lag in range(1, self.max_lag + 1):
                if lag in test_result:
                    # Use F-test result (more reliable)
                    f_test = test_result[lag][0]['ssr_ftest']
                    p_value = f_test[1]
                    f_stat = f_test[0]
                    
                    if p_value < best_p:
                        best_p = p_value
                        best_f = f_stat
                        best_lag = lag
            
            # Only return if significant
            if best_p < self.significance_level:
                return {
                    'best_lag': best_lag,
                    'p_value': best_p,
                    'f_stat': best_f
                }
            
            return None
            
        except Exception as e:
            # Log error in production, for now just return None
            return None
    
    def _is_stationary(self, series: pd.Series, threshold: float = 0.05) -> bool:
        """
        Check if series is stationary using Augmented Dickey-Fuller test.
        
        Args:
            series: Time series to test
            threshold: P-value threshold for stationarity
        
        Returns:
            True if stationary, False otherwise
        """
        try:
            from statsmodels.tsa.stattools import adfuller
            
            clean_series = series.dropna()
            if len(clean_series) < 10:
                return True  # Assume stationary if too few points
            
            result = adfuller(clean_series, autolag='AIC')
            return result[1] < threshold
        except Exception:
            return True  # Assume stationary if test fails
    
    def _determine_direction(
        self, 
        result_ab: Optional[Dict], 
        result_ba: Optional[Dict]
    ) -> CausalDirection:
        """
        Determine the causal direction from test results.
        
        Args:
            result_ab: Result of testing A→B
            result_ba: Result of testing B→A
        
        Returns:
            CausalDirection enum value
        """
        a_causes_b = result_ab is not None
        b_causes_a = result_ba is not None
        
        if a_causes_b and b_causes_a:
            return CausalDirection.bidirectional
        elif a_causes_b:
            return CausalDirection.a_causes_b
        elif b_causes_a:
            return CausalDirection.b_causes_a
        else:
            return CausalDirection.none
