from typing import List, Dict, Optional
from datetime import date
from collections import defaultdict

from app.ml.detectors.base import AnomalyResult
from app.ml.detectors.zscore import ZScoreDetector
from app.ml.detectors.isolation_forest import IsolationForestDetector
from app.utils.enums import DetectorType, Severity


class AnomalyEnsemble:
    """
    Combines results from multiple anomaly detectors.
    
    - Deduplicates anomalies detected by multiple detectors
    - Combines confidence scores
    - Ranks anomalies by severity and recency
    """
    
    def __init__(
        self,
        zscore_weight: float = 0.4,
        iforest_weight: float = 0.6,
    ):
        self.zscore_weight = zscore_weight
        self.iforest_weight = iforest_weight
    
    def combine(
        self,
        zscore_results: List[AnomalyResult],
        iforest_results: List[AnomalyResult],
        max_anomalies: int = 50,
    ) -> List[AnomalyResult]:
        """
        Combine results from Z-Score and Isolation Forest detectors.
        
        Args:
            zscore_results: Anomalies from Z-Score detector
            iforest_results: Anomalies from Isolation Forest detector
            max_anomalies: Maximum number of anomalies to return
        
        Returns:
            Combined and ranked list of anomalies
        """
        # Group anomalies by date
        anomalies_by_date: Dict[date, List[AnomalyResult]] = defaultdict(list)
        
        for anomaly in zscore_results:
            anomalies_by_date[anomaly.date].append(anomaly)
        
        for anomaly in iforest_results:
            anomalies_by_date[anomaly.date].append(anomaly)
        
        # Process each date
        combined_anomalies = []
        
        for anomaly_date, day_anomalies in anomalies_by_date.items():
            # Separate by detector type
            zscore_anomalies = [a for a in day_anomalies if a.detector_type == DetectorType.zscore]
            iforest_anomalies = [a for a in day_anomalies if a.detector_type == DetectorType.isolation_forest]
            
            # Check for overlap (same date flagged by both detectors)
            if zscore_anomalies and iforest_anomalies:
                # Create ensemble anomaly
                ensemble_anomaly = self._create_ensemble_anomaly(
                    zscore_anomalies, 
                    iforest_anomalies, 
                    anomaly_date
                )
                combined_anomalies.append(ensemble_anomaly)
                
                # Also keep individual zscore anomalies for specific metric insights
                for za in zscore_anomalies:
                    if za.metric_name != 'multivariate_anomaly':
                        combined_anomalies.append(za)
            else:
                # Keep all anomalies as-is
                combined_anomalies.extend(day_anomalies)
        
        # Deduplicate by (date, metric_name)
        seen = set()
        unique_anomalies = []
        for anomaly in combined_anomalies:
            key = (anomaly.date, anomaly.metric_name, anomaly.detector_type)
            if key not in seen:
                seen.add(key)
                unique_anomalies.append(anomaly)
        
        # Rank anomalies
        ranked = self._rank_anomalies(unique_anomalies)
        
        return ranked[:max_anomalies]
    
    def _create_ensemble_anomaly(
        self,
        zscore_anomalies: List[AnomalyResult],
        iforest_anomalies: List[AnomalyResult],
        anomaly_date: date,
    ) -> AnomalyResult:
        """Create a combined ensemble anomaly from multiple detector results"""
        
        # Calculate combined score
        max_zscore = max(a.anomaly_score for a in zscore_anomalies)
        max_iforest = max(a.anomaly_score for a in iforest_anomalies)
        
        combined_score = (
            self.zscore_weight * max_zscore + 
            self.iforest_weight * max_iforest
        )
        
        # Get primary metric from zscore (more interpretable)
        primary_zscore = max(zscore_anomalies, key=lambda a: a.anomaly_score)
        primary_iforest = max(iforest_anomalies, key=lambda a: a.anomaly_score)
        
        # Determine severity
        severity = self._combined_severity(combined_score)
        
        return AnomalyResult(
            date=anomaly_date,
            source_table='ensemble',
            source_id=primary_zscore.source_id,
            metric_name=f"{primary_zscore.metric_name}+multivariate",
            metric_value=primary_zscore.metric_value,
            baseline_value=primary_zscore.baseline_value,
            detector_type=DetectorType.ensemble,
            severity=severity,
            anomaly_score=round(combined_score, 3),
            details={
                'zscore_score': max_zscore,
                'iforest_score': max_iforest,
                'zscore_metrics': [a.metric_name for a in zscore_anomalies],
                'iforest_details': primary_iforest.details,
                'detection_agreement': True,
            }
        )
    
    def _combined_severity(self, score: float) -> Severity:
        """Determine severity from combined score"""
        if score >= 0.75:
            return Severity.high
        elif score >= 0.45:
            return Severity.medium
        else:
            return Severity.low
    
    def _rank_anomalies(self, anomalies: List[AnomalyResult]) -> List[AnomalyResult]:
        """Rank anomalies by severity, score, and recency"""
        
        severity_order = {
            Severity.high: 3,
            Severity.medium: 2,
            Severity.low: 1,
        }
        
        # Sort by: severity (desc), score (desc), date (desc)
        return sorted(
            anomalies,
            key=lambda a: (
                severity_order.get(a.severity, 0),
                a.anomaly_score,
                a.date.toordinal() if a.date else 0,
            ),
            reverse=True
        )
