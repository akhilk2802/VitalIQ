from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import date
import uuid

from app.utils.enums import DetectorType, Severity


@dataclass
class AnomalyResult:
    """Result from anomaly detection"""
    date: date
    source_table: str
    source_id: uuid.UUID
    metric_name: str
    metric_value: float
    baseline_value: float
    detector_type: DetectorType
    severity: Severity
    anomaly_score: float
    details: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        return {
            'date': self.date,
            'source_table': self.source_table,
            'source_id': self.source_id,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'baseline_value': self.baseline_value,
            'detector_type': self.detector_type,
            'severity': self.severity,
            'anomaly_score': self.anomaly_score,
            'details': self.details or {},
        }


class BaseDetector(ABC):
    """Base class for anomaly detectors"""
    
    detector_type: DetectorType
    
    @abstractmethod
    async def detect(self, **kwargs) -> List[AnomalyResult]:
        """Run anomaly detection and return results"""
        pass
    
    @staticmethod
    def score_to_severity(score: float) -> Severity:
        """Convert anomaly score to severity level"""
        if score >= 0.8:
            return Severity.high
        elif score >= 0.5:
            return Severity.medium
        else:
            return Severity.low
