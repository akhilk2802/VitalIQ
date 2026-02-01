from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.models.user import User
from app.models.anomaly import Anomaly
from app.ml.feature_engineering import FeatureEngineer
from app.ml.detectors.zscore import ZScoreDetector
from app.ml.detectors.isolation_forest import IsolationForestDetector
from app.ml.ensemble import AnomalyEnsemble
from app.ml.detectors.base import AnomalyResult


class AnomalyService:
    """Service for anomaly detection and management"""
    
    def __init__(self, db: AsyncSession, user_history_rag=None):
        self.db = db
        self._user_history_rag = user_history_rag
    
    @property
    def user_history_rag(self):
        """Lazy-load UserHistoryRAG to avoid circular imports."""
        if self._user_history_rag is None:
            from app.rag.user_history_rag import UserHistoryRAG
            self._user_history_rag = UserHistoryRAG(self.db)
        return self._user_history_rag
    
    async def detect_anomalies(
        self,
        user: User,
        days: int = 60,
        save_results: bool = True,
        use_robust: bool = True,
        use_adaptive: bool = True,
        use_ewma_baseline: bool = False,
    ) -> List[AnomalyResult]:
        """
        Run full anomaly detection pipeline with improved baseline calculation.
        
        Args:
            user: User to analyze
            days: Number of days of history to analyze
            save_results: Whether to persist results to database
            use_robust: Use median/IQR instead of mean/std (resistant to outliers)
            use_adaptive: Dynamically adjust thresholds based on data characteristics
            use_ewma_baseline: Use recent-weighted (EWMA) baseline instead of simple average
        
        Returns:
            List of detected anomalies
        """
        # Build feature matrix
        feature_eng = FeatureEngineer(self.db, user.id)
        feature_df = await feature_eng.build_daily_feature_matrix(days=days)
        
        # Calculate robust baselines with EWMA support
        baselines = await feature_eng.get_user_baselines(
            days=30, 
            use_robust=use_robust,
            ewma_span=7  # 7-day EWMA for recent trend weighting
        )
        
        if feature_df.empty:
            return []
        
        # Run detectors with improved settings
        zscore_detector = ZScoreDetector(
            use_robust=use_robust,
            use_adaptive=use_adaptive,
            use_ewma_baseline=use_ewma_baseline
        )
        iforest_detector = IsolationForestDetector()
        
        zscore_results = await zscore_detector.detect(
            feature_df=feature_df,
            baselines=baselines
        )
        
        iforest_results = await iforest_detector.detect(
            feature_df=feature_df,
            baselines=baselines
        )
        
        # Combine results
        ensemble = AnomalyEnsemble()
        combined_results = ensemble.combine(zscore_results, iforest_results)
        
        # Save to database if requested
        if save_results and combined_results:
            await self._save_anomalies(user.id, combined_results)
        
        return combined_results
    
    async def _save_anomalies(
        self, 
        user_id: uuid.UUID, 
        anomalies: List[AnomalyResult]
    ) -> List[Anomaly]:
        """Save detected anomalies to database"""
        saved = []
        
        for anomaly_result in anomalies:
            # Check if similar anomaly already exists
            existing = await self.db.execute(
                select(Anomaly).where(
                    and_(
                        Anomaly.user_id == user_id,
                        Anomaly.date == anomaly_result.date,
                        Anomaly.metric_name == anomaly_result.metric_name,
                        Anomaly.detector_type == anomaly_result.detector_type,
                    )
                )
            )
            
            if existing.scalar_one_or_none():
                continue  # Skip duplicate
            
            anomaly = Anomaly(
                user_id=user_id,
                date=anomaly_result.date,
                source_table=anomaly_result.source_table,
                source_id=anomaly_result.source_id,
                metric_name=anomaly_result.metric_name,
                metric_value=anomaly_result.metric_value,
                baseline_value=anomaly_result.baseline_value,
                detector_type=anomaly_result.detector_type,
                severity=anomaly_result.severity,
                anomaly_score=anomaly_result.anomaly_score,
            )
            
            self.db.add(anomaly)
            saved.append(anomaly)
        
        await self.db.flush()
        
        # Index anomalies for RAG retrieval (in background)
        for anomaly in saved:
            try:
                await self.user_history_rag.index_anomaly(anomaly)
            except Exception as e:
                # Don't fail the whole operation if indexing fails
                print(f"Failed to index anomaly {anomaly.id}: {e}")
        
        return saved
    
    async def get_anomalies(
        self,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100,
    ) -> List[Anomaly]:
        """Get anomalies for a user with optional filters"""
        query = select(Anomaly).where(Anomaly.user_id == user_id)
        
        if start_date:
            query = query.where(Anomaly.date >= start_date)
        if end_date:
            query = query.where(Anomaly.date <= end_date)
        if acknowledged is not None:
            query = query.where(Anomaly.is_acknowledged == acknowledged)
        
        query = query.order_by(Anomaly.detected_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def acknowledge_anomaly(
        self,
        user_id: uuid.UUID,
        anomaly_id: uuid.UUID,
    ) -> Optional[Anomaly]:
        """Mark an anomaly as acknowledged"""
        result = await self.db.execute(
            select(Anomaly).where(
                and_(
                    Anomaly.id == anomaly_id,
                    Anomaly.user_id == user_id,
                )
            )
        )
        anomaly = result.scalar_one_or_none()
        
        if anomaly:
            anomaly.is_acknowledged = True
            await self.db.flush()
        
        return anomaly
    
    async def get_anomaly_summary(
        self, 
        user_id: uuid.UUID, 
        days: int = 30
    ) -> dict:
        """Get summary statistics about anomalies"""
        from datetime import timedelta
        from app.utils.enums import Severity
        
        start_date = date.today() - timedelta(days=days)
        
        anomalies = await self.get_anomalies(
            user_id=user_id,
            start_date=start_date,
            limit=500
        )
        
        by_severity = {
            Severity.high: 0,
            Severity.medium: 0,
            Severity.low: 0,
        }
        
        by_metric = {}
        unacknowledged = 0
        
        for a in anomalies:
            by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
            by_metric[a.metric_name] = by_metric.get(a.metric_name, 0) + 1
            if not a.is_acknowledged:
                unacknowledged += 1
        
        return {
            'total': len(anomalies),
            'unacknowledged': unacknowledged,
            'by_severity': {k.value: v for k, v in by_severity.items()},
            'by_metric': by_metric,
            'period_days': days,
        }
