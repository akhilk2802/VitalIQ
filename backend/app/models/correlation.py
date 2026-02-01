import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Float, Boolean, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ENUM

from app.database import Base
from app.utils.enums import CorrelationType, CorrelationStrength, CausalDirection


class Correlation(Base):
    """
    Stores detected correlations between health metrics for a user.
    
    Supports multiple correlation types:
    - Pearson/Spearman: Linear/monotonic same-day correlations
    - Cross-correlation: Time-lagged relationships
    - Granger Causality: Predictive/causal relationships
    - Mutual Information: Non-linear dependencies
    """
    __tablename__ = "correlations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Metrics being correlated
    metric_a: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_b: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Correlation details
    correlation_type: Mapped[CorrelationType] = mapped_column(
        ENUM(CorrelationType, name='correlationtype', create_type=False),
        nullable=False
    )
    correlation_value: Mapped[float] = mapped_column(Float, nullable=False)
    strength: Mapped[CorrelationStrength] = mapped_column(
        ENUM(CorrelationStrength, name='correlationstrength', create_type=False),
        nullable=False
    )
    
    # Statistical significance
    p_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_significant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Time lag (for cross-correlation and Granger)
    lag_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Granger causality specific
    granger_f_stat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    causal_direction: Mapped[Optional[CausalDirection]] = mapped_column(
        ENUM(CausalDirection, name='causaldirection', create_type=False),
        nullable=True
    )
    
    # Granularity
    granularity: Mapped[str] = mapped_column(String(20), default="daily", nullable=False)
    
    # Analysis period
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # AI-generated insight
    insight: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Population comparison
    population_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    percentile_rank: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Metadata
    is_actionable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )
    
    # Relationships
    user = relationship("User", back_populates="correlations")

    def __repr__(self) -> str:
        return f"<Correlation({self.metric_a} <-> {self.metric_b}, type={self.correlation_type.value}, r={self.correlation_value:.3f})>"
