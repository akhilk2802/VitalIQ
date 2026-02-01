"""
Prediction Engine for VitalIQ

Provides predictive insights based on health data patterns:
- Recovery Readiness: Predicts body's readiness for activity
- Food Cravings: Predicts cravings with countermeasures
"""

from app.ml.prediction.recovery import RecoveryPredictor
from app.ml.prediction.cravings import CravingsPredictor

__all__ = ["RecoveryPredictor", "CravingsPredictor"]
