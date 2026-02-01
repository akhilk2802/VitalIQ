"""Base classes and data structures for correlation detection."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import pandas as pd

from app.utils.enums import CorrelationType, CorrelationStrength, CausalDirection


@dataclass
class CorrelationResult:
    """Result from a correlation detector."""
    
    metric_a: str
    metric_b: str
    correlation_type: CorrelationType
    correlation_value: float
    strength: CorrelationStrength
    p_value: Optional[float] = None
    is_significant: bool = False
    lag_days: int = 0
    granularity: str = "daily"
    sample_size: int = 0
    
    # Granger-specific
    causal_direction: Optional[CausalDirection] = None
    granger_f_stat: Optional[float] = None
    
    # Computed fields
    confidence: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'metric_a': self.metric_a,
            'metric_b': self.metric_b,
            'correlation_type': self.correlation_type.value,
            'correlation_value': self.correlation_value,
            'strength': self.strength.value,
            'p_value': self.p_value,
            'is_significant': self.is_significant,
            'lag_days': self.lag_days,
            'granularity': self.granularity,
            'sample_size': self.sample_size,
            'causal_direction': self.causal_direction.value if self.causal_direction else None,
            'granger_f_stat': self.granger_f_stat,
            'confidence': self.confidence,
            'details': self.details,
        }


class BaseCorrelationDetector(ABC):
    """Abstract base class for correlation detectors."""
    
    correlation_type: CorrelationType
    
    STRENGTH_THRESHOLDS = {
        'strong_positive': 0.7,
        'moderate_positive': 0.4,
        'weak_positive': 0.2,
        'negligible': -0.2,
        'weak_negative': -0.4,
        'moderate_negative': -0.7,
    }
    
    @abstractmethod
    async def detect(
        self,
        df: pd.DataFrame,
        metric_pairs: Optional[List[tuple]] = None
    ) -> List[CorrelationResult]:
        """
        Detect correlations in the data.
        
        Args:
            df: DataFrame with date index and metric columns
            metric_pairs: Optional list of (metric_a, metric_b) pairs to test
        
        Returns:
            List of detected correlations
        """
        pass
    
    @staticmethod
    def get_strength(value: float) -> CorrelationStrength:
        """Convert correlation value to strength label."""
        if value >= 0.7:
            return CorrelationStrength.strong_positive
        elif value >= 0.4:
            return CorrelationStrength.moderate_positive
        elif value >= 0.2:
            return CorrelationStrength.weak_positive
        elif value >= -0.2:
            return CorrelationStrength.negligible
        elif value >= -0.4:
            return CorrelationStrength.weak_negative
        elif value >= -0.7:
            return CorrelationStrength.moderate_negative
        else:
            return CorrelationStrength.strong_negative
    
    @staticmethod
    def get_meaningful_pairs(columns: List[str]) -> List[tuple]:
        """
        Generate meaningful metric pairs to test.
        
        Focuses on likely cause-effect relationships between health metrics.
        """
        # Define which metrics are likely to influence others
        influencers = {
            'exercise_minutes', 'exercise_calories', 'exercise_intensity_avg',
            'total_calories', 'total_protein_g', 'total_carbs_g', 'total_sugar_g', 'total_fats_g',
            'sleep_hours', 'sleep_quality',
        }
        
        outcomes = {
            'sleep_hours', 'sleep_quality', 'awakenings',
            'resting_hr', 'hrv', 'bp_systolic', 'bp_diastolic',
            'blood_glucose_fasting', 'blood_glucose_post_meal',
            'weight_kg', 'body_fat_pct',
        }
        
        pairs = []
        for inf in influencers:
            for out in outcomes:
                if inf != out and inf in columns and out in columns:
                    pairs.append((inf, out))
        
        return pairs
