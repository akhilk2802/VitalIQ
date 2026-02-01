"""
Correlation Service - business logic for correlation detection and management.
"""

from typing import List, Optional, Dict
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
import uuid

from app.models.user import User
from app.models.correlation import Correlation
from app.ml.feature_engineering import FeatureEngineer
from app.ml.correlation.aggregator import CorrelationAggregator
from app.ml.correlation.population import PopulationBaseline
from app.ml.correlation.base import CorrelationResult
from app.utils.enums import CorrelationType, CorrelationStrength


class CorrelationService:
    """Service for correlation detection and management."""
    
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
    
    async def detect_correlations(
        self,
        user: User,
        days: int = 60,
        include_granger: bool = True,
        include_pearson: bool = True,
        include_cross_correlation: bool = True,
        include_mutual_info: bool = True,
        include_population_comparison: bool = True,
        min_confidence: float = 0.3,
        save_results: bool = True
    ) -> List[CorrelationResult]:
        """
        Run full correlation detection pipeline.
        
        Args:
            user: User to analyze
            days: Number of days of history to analyze
            include_granger: Run Granger causality tests
            include_pearson: Run Pearson/Spearman correlations
            include_cross_correlation: Run time-lagged correlations
            include_mutual_info: Run mutual information tests
            include_population_comparison: Add population stats
            min_confidence: Minimum confidence to save
            save_results: Whether to persist to database
        
        Returns:
            List of detected correlations
        """
        # Build feature matrix
        feature_eng = FeatureEngineer(self.db, user.id)
        daily_df = await feature_eng.build_daily_feature_matrix(days=days)
        
        if daily_df.empty or len(daily_df) < 14:
            return []
        
        # Compute period
        period_start = date.today() - timedelta(days=days)
        period_end = date.today()
        
        # Run correlation aggregator
        aggregator = CorrelationAggregator(
            include_granger=include_granger,
            include_pearson=include_pearson,
            include_cross_correlation=include_cross_correlation,
            include_mutual_info=include_mutual_info
        )
        
        results = await aggregator.analyze(
            daily_df=daily_df,
            period_start=period_start,
            period_end=period_end
        )
        
        # Filter by minimum confidence
        results = [r for r in results if r.confidence >= min_confidence]
        
        # Add population comparison
        if include_population_comparison and results:
            pop_baseline = PopulationBaseline(self.db)
            results = await pop_baseline.enrich_with_population_stats(results, user.id)
        
        # Save to database
        if save_results and results:
            await self._save_correlations(user.id, results, period_start, period_end)
        
        return results
    
    async def _save_correlations(
        self,
        user_id: uuid.UUID,
        results: List[CorrelationResult],
        period_start: date,
        period_end: date
    ) -> List[Correlation]:
        """Save correlation results to database."""
        saved = []
        
        # First, delete old correlations for this user in the same period
        # (to avoid duplicates on re-run)
        await self.db.execute(
            delete(Correlation).where(
                and_(
                    Correlation.user_id == user_id,
                    Correlation.period_start == period_start,
                    Correlation.period_end == period_end
                )
            )
        )
        
        for result in results:
            correlation = Correlation(
                user_id=user_id,
                metric_a=result.metric_a,
                metric_b=result.metric_b,
                correlation_type=result.correlation_type,
                correlation_value=result.correlation_value,
                strength=result.strength,
                p_value=result.p_value,
                is_significant=result.is_significant,
                lag_days=result.lag_days,
                granger_f_stat=result.granger_f_stat,
                causal_direction=result.causal_direction,
                granularity=result.granularity,
                period_start=period_start,
                period_end=period_end,
                sample_size=result.sample_size,
                population_avg=result.details.get('population_avg'),
                percentile_rank=result.details.get('percentile_rank'),
                is_actionable=result.details.get('is_actionable', False),
                confidence_score=result.confidence,
            )
            
            self.db.add(correlation)
            saved.append(correlation)
        
        await self.db.flush()
        
        # Index correlations for RAG retrieval
        for correlation in saved:
            try:
                await self.user_history_rag.index_correlation(correlation)
            except Exception as e:
                # Don't fail the whole operation if indexing fails
                print(f"Failed to index correlation {correlation.id}: {e}")
        
        return saved
    
    async def get_correlations(
        self,
        user_id: uuid.UUID,
        correlation_type: Optional[CorrelationType] = None,
        actionable_only: bool = False,
        min_strength: Optional[CorrelationStrength] = None,
        limit: int = 50
    ) -> List[Correlation]:
        """Get correlations for a user with optional filters."""
        query = select(Correlation).where(Correlation.user_id == user_id)
        
        if correlation_type:
            query = query.where(Correlation.correlation_type == correlation_type)
        
        if actionable_only:
            query = query.where(Correlation.is_actionable == True)
        
        # Order by confidence/strength
        query = query.order_by(Correlation.confidence_score.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_correlation_by_id(
        self,
        user_id: uuid.UUID,
        correlation_id: uuid.UUID
    ) -> Optional[Correlation]:
        """Get a specific correlation by ID."""
        result = await self.db.execute(
            select(Correlation).where(
                and_(
                    Correlation.id == correlation_id,
                    Correlation.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_top_actionable(
        self,
        user_id: uuid.UUID,
        limit: int = 5
    ) -> List[Correlation]:
        """Get top actionable correlations for dashboard."""
        result = await self.db.execute(
            select(Correlation).where(
                and_(
                    Correlation.user_id == user_id,
                    Correlation.is_actionable == True
                )
            ).order_by(Correlation.confidence_score.desc()).limit(limit)
        )
        return result.scalars().all()
    
    async def get_correlation_summary(
        self,
        user_id: uuid.UUID,
        days: int = 30
    ) -> Dict:
        """Get summary statistics about correlations."""
        correlations = await self.get_correlations(
            user_id=user_id,
            limit=200
        )
        
        if not correlations:
            return {
                'total': 0,
                'significant': 0,
                'actionable': 0,
                'by_type': {},
                'by_strength': {},
                'top_pairs': []
            }
        
        by_type = {}
        by_strength = {}
        
        for c in correlations:
            type_name = c.correlation_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
            
            strength = c.strength.value
            by_strength[strength] = by_strength.get(strength, 0) + 1
        
        # Top pairs
        top_pairs = [
            f"{c.metric_a} ↔ {c.metric_b}"
            for c in correlations[:5]
        ]
        
        return {
            'total': len(correlations),
            'significant': sum(1 for c in correlations if c.is_significant),
            'actionable': sum(1 for c in correlations if c.is_actionable),
            'by_type': by_type,
            'by_strength': by_strength,
            'top_pairs': top_pairs
        }
    
    async def update_correlation_insight(
        self,
        correlation_id: uuid.UUID,
        user_id: uuid.UUID,
        insight: str,
        recommendation: str
    ) -> Optional[Correlation]:
        """Update AI-generated insight for a correlation."""
        correlation = await self.get_correlation_by_id(user_id, correlation_id)
        
        if correlation:
            correlation.insight = insight
            correlation.recommendation = recommendation
            await self.db.flush()
        
        return correlation
