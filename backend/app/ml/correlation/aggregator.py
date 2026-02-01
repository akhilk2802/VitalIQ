"""
Correlation Aggregator - combines results from all correlation detectors.

Handles:
- Running all detectors
- Deduplicating overlapping results
- Ranking by importance/confidence
- Determining actionability
"""

import pandas as pd
from typing import List, Optional, Dict
from datetime import date

from app.ml.correlation.base import CorrelationResult
from app.ml.correlation.granger import GrangerCausalityDetector
from app.ml.correlation.pearson import PearsonSpearmanDetector
from app.ml.correlation.cross_correlation import CrossCorrelationDetector
from app.ml.correlation.mutual_info import MutualInformationDetector
from app.utils.enums import CorrelationType, CorrelationStrength


class CorrelationAggregator:
    """
    Aggregates results from multiple correlation detectors.
    
    Runs all detection algorithms, deduplicates results,
    and ranks them by significance and actionability.
    """
    
    # Thresholds for actionability
    ACTIONABLE_THRESHOLDS = {
        'min_correlation': 0.5,      # |r| > 0.5
        'min_confidence': 0.6,       # confidence > 0.6
        'granger_significant': True,  # Any significant Granger result
        'strong_correlation': 0.7,    # |r| > 0.7 always actionable
    }
    
    def __init__(
        self,
        include_granger: bool = True,
        include_pearson: bool = True,
        include_cross_correlation: bool = True,
        include_mutual_info: bool = True,
        max_lag: int = 3,
        significance_level: float = 0.05,
        min_samples: int = 14
    ):
        """
        Initialize the aggregator with detection options.
        
        Args:
            include_granger: Run Granger causality tests
            include_pearson: Run Pearson/Spearman correlations
            include_cross_correlation: Run time-lagged correlations
            include_mutual_info: Run mutual information tests
            max_lag: Maximum lag days for time-series tests
            significance_level: P-value threshold
            min_samples: Minimum data points required
        """
        self.include_granger = include_granger
        self.include_pearson = include_pearson
        self.include_cross_correlation = include_cross_correlation
        self.include_mutual_info = include_mutual_info
        
        self.max_lag = max_lag
        self.significance_level = significance_level
        self.min_samples = min_samples
    
    async def analyze(
        self,
        daily_df: pd.DataFrame,
        weekly_df: Optional[pd.DataFrame] = None,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> List[CorrelationResult]:
        """
        Run all correlation analyses and aggregate results.
        
        Args:
            daily_df: Daily feature matrix
            weekly_df: Optional weekly aggregated data
            period_start: Start of analysis period
            period_end: End of analysis period
        
        Returns:
            Deduplicated, ranked list of correlations
        """
        all_results = []
        
        # 1. Pearson/Spearman (same-day linear)
        if self.include_pearson:
            detector = PearsonSpearmanDetector(
                significance_level=self.significance_level,
                min_samples=self.min_samples
            )
            results = await detector.detect(daily_df)
            all_results.extend(results)
        
        # 2. Cross-correlation (time-lagged)
        if self.include_cross_correlation:
            detector = CrossCorrelationDetector(
                max_lag=self.max_lag,
                significance_level=self.significance_level,
                min_samples=self.min_samples
            )
            results = await detector.detect(daily_df)
            all_results.extend(results)
        
        # 3. Granger Causality (predictive)
        if self.include_granger:
            detector = GrangerCausalityDetector(
                max_lag=self.max_lag,
                significance_level=self.significance_level,
                min_samples=max(20, self.min_samples)  # Granger needs more data
            )
            results = await detector.detect(daily_df)
            all_results.extend(results)
        
        # 4. Mutual Information (non-linear)
        if self.include_mutual_info:
            detector = MutualInformationDetector(
                min_samples=self.min_samples
            )
            results = await detector.detect(daily_df)
            all_results.extend(results)
        
        # 5. Weekly correlations (if data provided)
        if weekly_df is not None and len(weekly_df) >= 4 and self.include_pearson:
            detector = PearsonSpearmanDetector(
                significance_level=self.significance_level,
                min_samples=4
            )
            weekly_results = await detector.detect(weekly_df)
            
            # Mark as weekly granularity
            for r in weekly_results:
                r.granularity = "weekly"
            
            all_results.extend(weekly_results)
        
        # Deduplicate and rank
        final_results = self._deduplicate_and_rank(all_results)
        
        # Mark actionable correlations
        for result in final_results:
            result.details['is_actionable'] = self._is_actionable(result)
        
        return final_results
    
    def _deduplicate_and_rank(
        self, 
        results: List[CorrelationResult]
    ) -> List[CorrelationResult]:
        """
        Deduplicate overlapping correlations and rank by importance.
        
        Keeps the best result for each metric pair, preferring:
        1. Granger causality (most informative)
        2. Cross-correlation (predictive)
        3. Pearson/Spearman (basic)
        4. Mutual Information (non-linear, supplementary)
        """
        # Priority order for correlation types
        type_priority = {
            CorrelationType.granger_causality: 4,
            CorrelationType.cross_correlation: 3,
            CorrelationType.pearson: 2,
            CorrelationType.spearman: 2,
            CorrelationType.mutual_information: 1,
        }
        
        # Group by metric pair (order-independent) and granularity
        seen: Dict[tuple, CorrelationResult] = {}
        
        for result in results:
            # Create order-independent key
            pair = frozenset([result.metric_a, result.metric_b])
            key = (pair, result.granularity)
            
            if key not in seen:
                seen[key] = result
            else:
                existing = seen[key]
                
                # Compare by: 1) type priority, 2) confidence
                existing_priority = type_priority.get(existing.correlation_type, 0)
                new_priority = type_priority.get(result.correlation_type, 0)
                
                if new_priority > existing_priority:
                    seen[key] = result
                elif new_priority == existing_priority and result.confidence > existing.confidence:
                    seen[key] = result
        
        # Convert to list and sort by confidence
        ranked = list(seen.values())
        ranked.sort(key=lambda x: (
            type_priority.get(x.correlation_type, 0),  # Type priority first
            x.confidence  # Then confidence
        ), reverse=True)
        
        return ranked
    
    def _is_actionable(self, result: CorrelationResult) -> bool:
        """
        Determine if a correlation should trigger alerts/recommendations.
        
        Criteria:
        - Strong correlation (|r| > 0.7)
        - Significant Granger causality
        - High-confidence time-lagged correlation
        """
        abs_corr = abs(result.correlation_value)
        
        # Always actionable for strong correlations
        if abs_corr >= self.ACTIONABLE_THRESHOLDS['strong_correlation']:
            return True
        
        # Granger causality is inherently actionable if significant
        if result.correlation_type == CorrelationType.granger_causality:
            if result.is_significant and result.causal_direction:
                return True
        
        # Time-lagged correlations are actionable if predictive
        if result.correlation_type == CorrelationType.cross_correlation:
            if result.lag_days > 0 and abs_corr >= self.ACTIONABLE_THRESHOLDS['min_correlation']:
                return True
        
        # High confidence correlations
        if (result.confidence >= self.ACTIONABLE_THRESHOLDS['min_confidence'] and
            abs_corr >= self.ACTIONABLE_THRESHOLDS['min_correlation']):
            return True
        
        return False
    
    def get_top_actionable(
        self, 
        results: List[CorrelationResult],
        limit: int = 5
    ) -> List[CorrelationResult]:
        """Get top N actionable correlations."""
        actionable = [r for r in results if r.details.get('is_actionable', False)]
        return actionable[:limit]
    
    def summarize_findings(
        self, 
        results: List[CorrelationResult]
    ) -> Dict:
        """
        Generate a summary of correlation findings.
        
        Returns:
            Dict with counts and key findings
        """
        if not results:
            return {
                'total_correlations': 0,
                'significant_count': 0,
                'actionable_count': 0,
                'by_type': {},
                'by_strength': {},
                'top_findings': []
            }
        
        # Count by type
        by_type = {}
        for r in results:
            type_name = r.correlation_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        # Count by strength
        by_strength = {}
        for r in results:
            strength = r.strength.value
            by_strength[strength] = by_strength.get(strength, 0) + 1
        
        # Top findings (human-readable)
        top_findings = []
        for r in results[:5]:
            if r.correlation_type == CorrelationType.granger_causality:
                finding = f"{r.metric_a} predicts {r.metric_b} (lag: {r.lag_days} day)"
            elif r.correlation_type == CorrelationType.cross_correlation:
                finding = f"{r.metric_a} affects {r.metric_b} after {r.lag_days} day(s)"
            else:
                direction = "positively" if r.correlation_value > 0 else "negatively"
                finding = f"{r.metric_a} and {r.metric_b} are {direction} correlated"
            top_findings.append(finding)
        
        return {
            'total_correlations': len(results),
            'significant_count': sum(1 for r in results if r.is_significant),
            'actionable_count': sum(1 for r in results if r.details.get('is_actionable', False)),
            'by_type': by_type,
            'by_strength': by_strength,
            'top_findings': top_findings
        }
