"""
Population baseline comparison for correlations.

Compares individual user's correlations against population averages
to identify unique patterns and provide percentile rankings.
"""

import numpy as np
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

from app.models.correlation import Correlation
from app.ml.correlation.base import CorrelationResult
from app.utils.enums import CorrelationType


class PopulationBaseline:
    """
    Computes and compares correlations against population baselines.
    
    Provides:
    - Population average correlation for each metric pair
    - Percentile ranking of user's correlation vs population
    - Flags for unusually strong/weak correlations
    """
    
    # Default population baselines (used when not enough users)
    # These are based on typical health data research findings
    DEFAULT_BASELINES = {
        # (metric_a, metric_b): (avg_correlation, std_dev)
        ('exercise_minutes', 'sleep_quality'): (0.35, 0.15),
        ('exercise_minutes', 'resting_hr'): (-0.25, 0.12),
        ('total_calories', 'weight_kg'): (0.20, 0.18),
        ('sleep_hours', 'hrv'): (0.30, 0.14),
        ('total_sugar_g', 'sleep_quality'): (-0.18, 0.10),
        ('sleep_quality', 'resting_hr'): (-0.22, 0.11),
        ('exercise_minutes', 'hrv'): (0.28, 0.13),
        ('total_carbs_g', 'blood_glucose_fasting'): (0.25, 0.15),
    }
    
    MIN_USERS_FOR_POPULATION = 10  # Minimum users needed to compute population stats
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compute_population_stats(
        self,
        metric_a: str,
        metric_b: str,
        correlation_type: CorrelationType,
        exclude_user_id: Optional[uuid.UUID] = None
    ) -> Optional[Dict]:
        """
        Compute population statistics for a metric pair.
        
        Args:
            metric_a: First metric
            metric_b: Second metric
            correlation_type: Type of correlation
            exclude_user_id: User to exclude from population (typically current user)
        
        Returns:
            Dict with mean, std, count, or None if insufficient data
        """
        query = select(
            func.avg(Correlation.correlation_value).label('mean'),
            func.stddev(Correlation.correlation_value).label('std'),
            func.count(Correlation.id).label('count')
        ).where(
            Correlation.metric_a == metric_a,
            Correlation.metric_b == metric_b,
            Correlation.correlation_type == correlation_type
        )
        
        if exclude_user_id:
            query = query.where(Correlation.user_id != exclude_user_id)
        
        result = await self.db.execute(query)
        row = result.one_or_none()
        
        if not row or row.count < self.MIN_USERS_FOR_POPULATION:
            # Fall back to default baselines
            return self._get_default_baseline(metric_a, metric_b)
        
        return {
            'mean': float(row.mean) if row.mean else 0.0,
            'std': float(row.std) if row.std else 0.1,
            'count': row.count
        }
    
    def _get_default_baseline(
        self, 
        metric_a: str, 
        metric_b: str
    ) -> Optional[Dict]:
        """Get default baseline for a metric pair."""
        # Try both orderings
        key = (metric_a, metric_b)
        reverse_key = (metric_b, metric_a)
        
        if key in self.DEFAULT_BASELINES:
            avg, std = self.DEFAULT_BASELINES[key]
            return {'mean': avg, 'std': std, 'count': 0, 'is_default': True}
        elif reverse_key in self.DEFAULT_BASELINES:
            avg, std = self.DEFAULT_BASELINES[reverse_key]
            return {'mean': avg, 'std': std, 'count': 0, 'is_default': True}
        
        # No default available - use neutral baseline
        return {'mean': 0.0, 'std': 0.25, 'count': 0, 'is_default': True}
    
    def compute_percentile(
        self,
        user_value: float,
        population_mean: float,
        population_std: float
    ) -> float:
        """
        Compute percentile rank of user's correlation vs population.
        
        Uses normal distribution approximation.
        
        Args:
            user_value: User's correlation value
            population_mean: Population average
            population_std: Population standard deviation
        
        Returns:
            Percentile (0-100)
        """
        from scipy import stats
        
        if population_std <= 0:
            population_std = 0.1  # Avoid division by zero
        
        # Z-score of user's value
        z = (user_value - population_mean) / population_std
        
        # Convert to percentile (for absolute value - strength matters, not direction)
        percentile = stats.norm.cdf(abs(z)) * 100
        
        return round(percentile, 1)
    
    async def enrich_with_population_stats(
        self,
        results: List[CorrelationResult],
        user_id: uuid.UUID
    ) -> List[CorrelationResult]:
        """
        Add population comparison data to correlation results.
        
        Args:
            results: List of correlation results to enrich
            user_id: Current user's ID (to exclude from population)
        
        Returns:
            Results with population_avg and percentile_rank added
        """
        for result in results:
            # Get population stats
            pop_stats = await self.compute_population_stats(
                result.metric_a,
                result.metric_b,
                result.correlation_type,
                exclude_user_id=user_id
            )
            
            if pop_stats:
                result.details['population_avg'] = pop_stats['mean']
                result.details['population_std'] = pop_stats['std']
                result.details['population_count'] = pop_stats['count']
                result.details['is_default_baseline'] = pop_stats.get('is_default', False)
                
                # Compute percentile
                percentile = self.compute_percentile(
                    result.correlation_value,
                    pop_stats['mean'],
                    pop_stats['std']
                )
                result.details['percentile_rank'] = percentile
                
                # Flag unusual correlations (>1.5 std from population)
                z_score = abs(result.correlation_value - pop_stats['mean']) / max(pop_stats['std'], 0.1)
                result.details['is_unusual'] = z_score > 1.5
                result.details['z_vs_population'] = round(z_score, 2)
        
        return results
    
    async def get_population_anomalies(
        self,
        results: List[CorrelationResult],
        threshold_percentile: float = 90
    ) -> List[CorrelationResult]:
        """
        Get correlations that are unusually different from population.
        
        Args:
            results: Enriched correlation results
            threshold_percentile: Minimum percentile to flag (default: top 10%)
        
        Returns:
            Correlations that are significantly different from population
        """
        anomalies = []
        
        for result in results:
            percentile = result.details.get('percentile_rank', 50)
            if percentile >= threshold_percentile:
                anomalies.append(result)
        
        return anomalies
