from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import uuid

from app.utils.enums import DetectorType, Severity


class AnomalyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    date: date
    source_table: str
    source_id: uuid.UUID
    metric_name: str
    metric_value: float
    baseline_value: float
    detector_type: DetectorType
    severity: Severity
    anomaly_score: float
    explanation: Optional[str]
    is_acknowledged: bool
    detected_at: datetime

    class Config:
        from_attributes = True


class AnomalyDetectionRequest(BaseModel):
    days: int = 60  # Number of days to analyze
    include_explanation: bool = True  # Whether to generate LLM explanations
    # Improved baseline settings
    use_robust: bool = True  # Use median/IQR instead of mean/std (resistant to outliers)
    use_adaptive: bool = True  # Dynamically adjust thresholds based on data variance
    use_ewma_baseline: bool = False  # Use recent-weighted (EWMA) baseline


class AnomalyDetectionResult(BaseModel):
    total_anomalies: int
    new_anomalies: int
    anomalies: List[AnomalyResponse]


class AnomalyAcknowledge(BaseModel):
    is_acknowledged: bool = True


class InsightResponse(BaseModel):
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    anomaly_count: int
    period_days: int
    generated_at: datetime
