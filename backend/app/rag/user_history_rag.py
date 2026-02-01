"""
User History RAG Service for personalized context retrieval.

Indexes and retrieves user-specific:
- Past anomalies with explanations
- Detected correlations with insights
- Generated insights
- Chat conversation history
"""

import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.rag.embedding_service import EmbeddingService
from app.rag.vector_service import VectorService
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.models.user_history_embedding import UserHistoryEmbedding
from app.utils.enums import HistoryEntityType
from app.config import settings


@dataclass
class HistoryChunk:
    """Represents a retrieved user history chunk."""
    content: str
    entity_type: str
    entity_id: Optional[str]
    similarity: float
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    
    def to_context_string(self) -> str:
        """Format as context string for LLM prompt."""
        type_labels = {
            "anomaly": "Past Anomaly",
            "correlation": "Correlation",
            "insight": "Previous Insight",
            "chat_message": "Previous Conversation",
        }
        label = type_labels.get(self.entity_type, self.entity_type.title())
        
        date_str = ""
        if self.metadata and self.metadata.get("date"):
            date_str = f" ({self.metadata['date']})"
        
        return f"[{label}{date_str}]\n{self.content}"


class UserHistoryRAG:
    """
    RAG service for user-specific history retrieval.
    
    Provides personalized context by indexing and retrieving:
    - Anomalies the user has experienced
    - Correlations detected for the user
    - AI-generated insights
    - Chat messages for conversation memory
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService(db)
    
    # ==================== Indexing Methods ====================
    
    async def index_anomaly(self, anomaly: Anomaly) -> Optional[uuid.UUID]:
        """
        Index an anomaly for later retrieval.
        
        Creates a text representation and embeds it.
        
        Args:
            anomaly: Anomaly to index
            
        Returns:
            ID of created embedding or None if no explanation
        """
        # Build content text
        content = self._build_anomaly_content(anomaly)
        
        if not content:
            return None
        
        # Generate embedding
        embedding = await self.embedding_service.generate_embedding(content)
        
        # Build metadata
        metadata = {
            "date": str(anomaly.date),
            "metric_name": anomaly.metric_name,
            "metric_value": anomaly.metric_value,
            "baseline_value": anomaly.baseline_value,
            "severity": anomaly.severity.value if anomaly.severity else None,
            "detector_type": anomaly.detector_type.value if anomaly.detector_type else None,
        }
        
        # Delete any existing embedding for this anomaly
        await self.vector_service.delete_user_history_embeddings(
            user_id=anomaly.user_id,
            entity_type=HistoryEntityType.anomaly,
            entity_id=anomaly.id
        )
        
        # Create new embedding
        return await self.vector_service.upsert_user_history_embedding(
            user_id=anomaly.user_id,
            content=content,
            embedding=embedding,
            entity_type=HistoryEntityType.anomaly,
            entity_id=anomaly.id,
            metadata=metadata
        )
    
    def _build_anomaly_content(self, anomaly: Anomaly) -> str:
        """Build text content for anomaly embedding."""
        metric_name = anomaly.metric_name.replace("_", " ").title()
        direction = "higher" if anomaly.metric_value > anomaly.baseline_value else "lower"
        
        parts = [
            f"On {anomaly.date}, {metric_name} was {direction} than usual.",
            f"Value: {anomaly.metric_value}, Baseline: {anomaly.baseline_value}.",
            f"Severity: {anomaly.severity.value if anomaly.severity else 'unknown'}.",
        ]
        
        if anomaly.explanation:
            parts.append(f"Explanation: {anomaly.explanation}")
        
        return " ".join(parts)
    
    async def index_correlation(self, correlation: Correlation) -> Optional[uuid.UUID]:
        """
        Index a correlation for later retrieval.
        
        Args:
            correlation: Correlation to index
            
        Returns:
            ID of created embedding
        """
        content = self._build_correlation_content(correlation)
        
        if not content:
            return None
        
        embedding = await self.embedding_service.generate_embedding(content)
        
        metadata = {
            "metric_a": correlation.metric_a,
            "metric_b": correlation.metric_b,
            "correlation_type": correlation.correlation_type.value,
            "correlation_value": correlation.correlation_value,
            "strength": correlation.strength.value if correlation.strength else None,
            "lag_days": correlation.lag_days,
            "period_start": str(correlation.period_start),
            "period_end": str(correlation.period_end),
        }
        
        # Delete existing
        await self.vector_service.delete_user_history_embeddings(
            user_id=correlation.user_id,
            entity_type=HistoryEntityType.correlation,
            entity_id=correlation.id
        )
        
        return await self.vector_service.upsert_user_history_embedding(
            user_id=correlation.user_id,
            content=content,
            embedding=embedding,
            entity_type=HistoryEntityType.correlation,
            entity_id=correlation.id,
            metadata=metadata
        )
    
    def _build_correlation_content(self, correlation: Correlation) -> str:
        """Build text content for correlation embedding."""
        metric_a = correlation.metric_a.replace("_", " ").title()
        metric_b = correlation.metric_b.replace("_", " ").title()
        
        direction = "positively" if correlation.correlation_value > 0 else "negatively"
        strength = correlation.strength.value.replace("_", " ") if correlation.strength else "moderate"
        
        parts = [
            f"{metric_a} and {metric_b} are {direction} correlated ({strength}).",
            f"Correlation value: {correlation.correlation_value:.3f}.",
        ]
        
        if correlation.lag_days > 0:
            parts.append(f"Effect appears after {correlation.lag_days} day(s).")
        
        if correlation.causal_direction:
            if correlation.causal_direction.value == "a_causes_b":
                parts.append(f"{metric_a} appears to influence {metric_b}.")
            elif correlation.causal_direction.value == "b_causes_a":
                parts.append(f"{metric_b} appears to influence {metric_a}.")
        
        if correlation.insight:
            parts.append(f"Insight: {correlation.insight}")
        
        if correlation.recommendation:
            parts.append(f"Recommendation: {correlation.recommendation}")
        
        return " ".join(parts)
    
    async def index_insight(
        self,
        user_id: uuid.UUID,
        insight: str,
        context: Dict[str, Any]
    ) -> uuid.UUID:
        """
        Index a generated insight.
        
        Args:
            user_id: User ID
            insight: The insight text
            context: Additional context (metrics involved, date range, etc.)
            
        Returns:
            ID of created embedding
        """
        embedding = await self.embedding_service.generate_embedding(insight)
        
        metadata = {
            "generated_at": datetime.utcnow().isoformat(),
            **context
        }
        
        return await self.vector_service.upsert_user_history_embedding(
            user_id=user_id,
            content=insight,
            embedding=embedding,
            entity_type=HistoryEntityType.insight,
            entity_id=None,
            metadata=metadata
        )
    
    async def index_chat_message(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        content: str,
        role: str
    ) -> uuid.UUID:
        """
        Index a chat message for conversation memory.
        
        Args:
            user_id: User ID
            message_id: Chat message ID
            content: Message content
            role: Message role (user/assistant)
            
        Returns:
            ID of created embedding
        """
        # Add role prefix for context
        prefixed_content = f"[{role.upper()}]: {content}"
        
        embedding = await self.embedding_service.generate_embedding(prefixed_content)
        
        metadata = {
            "role": role,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return await self.vector_service.upsert_user_history_embedding(
            user_id=user_id,
            content=prefixed_content,
            embedding=embedding,
            entity_type=HistoryEntityType.chat_message,
            entity_id=message_id,
            metadata=metadata
        )
    
    # ==================== Retrieval Methods ====================
    
    async def retrieve_similar_anomalies(
        self,
        user_id: uuid.UUID,
        current_anomaly: Anomaly,
        k: int = 3
    ) -> List[HistoryChunk]:
        """
        Find similar past anomalies for context.
        
        Args:
            user_id: User ID
            current_anomaly: Current anomaly to find similar to
            k: Number of results
            
        Returns:
            List of similar past anomalies
        """
        # Build query from current anomaly
        query = self._build_anomaly_content(current_anomaly)
        
        query_embedding = await self.embedding_service.generate_query_embedding(query)
        
        results = await self.vector_service.similarity_search_user_history(
            query_embedding=query_embedding,
            user_id=user_id,
            k=k + 1,  # Get extra to filter out current
            entity_types=[HistoryEntityType.anomaly],
            threshold=0.4
        )
        
        # Filter out the current anomaly
        chunks = []
        for r in results:
            if r["entity_id"] != str(current_anomaly.id):
                chunks.append(HistoryChunk(
                    content=r["content"],
                    entity_type=r["entity_type"],
                    entity_id=r["entity_id"],
                    similarity=r["similarity"],
                    metadata=r["metadata"],
                    created_at=r["created_at"]
                ))
        
        return chunks[:k]
    
    async def retrieve_relevant_history(
        self,
        user_id: uuid.UUID,
        query: str,
        k: int = 5,
        entity_types: Optional[List[HistoryEntityType]] = None
    ) -> List[HistoryChunk]:
        """
        Retrieve relevant user history for a query.
        
        Args:
            user_id: User ID
            query: Search query
            k: Number of results
            entity_types: Filter by entity types (default: all)
            
        Returns:
            List of relevant history chunks
        """
        query_embedding = await self.embedding_service.generate_query_embedding(query)
        
        results = await self.vector_service.similarity_search_user_history(
            query_embedding=query_embedding,
            user_id=user_id,
            k=k,
            entity_types=entity_types,
            threshold=0.3
        )
        
        return [
            HistoryChunk(
                content=r["content"],
                entity_type=r["entity_type"],
                entity_id=r["entity_id"],
                similarity=r["similarity"],
                metadata=r["metadata"],
                created_at=r["created_at"]
            )
            for r in results
        ]
    
    async def get_user_patterns(
        self,
        user_id: uuid.UUID,
        metric: str,
        k: int = 5
    ) -> List[HistoryChunk]:
        """
        Get patterns related to a specific metric.
        
        Args:
            user_id: User ID
            metric: Metric name
            k: Number of results
            
        Returns:
            Anomalies and correlations related to the metric
        """
        query = f"patterns and anomalies for {metric.replace('_', ' ')}"
        
        query_embedding = await self.embedding_service.generate_query_embedding(query)
        
        results = await self.vector_service.similarity_search_user_history(
            query_embedding=query_embedding,
            user_id=user_id,
            k=k,
            entity_types=[HistoryEntityType.anomaly, HistoryEntityType.correlation],
            threshold=0.3
        )
        
        return [
            HistoryChunk(
                content=r["content"],
                entity_type=r["entity_type"],
                entity_id=r["entity_id"],
                similarity=r["similarity"],
                metadata=r["metadata"],
                created_at=r["created_at"]
            )
            for r in results
        ]
    
    async def get_conversation_context(
        self,
        user_id: uuid.UUID,
        current_message: str,
        k: int = 3
    ) -> List[HistoryChunk]:
        """
        Get relevant past conversation context.
        
        Args:
            user_id: User ID
            current_message: Current user message
            k: Number of relevant past messages
            
        Returns:
            Relevant past conversation chunks
        """
        query_embedding = await self.embedding_service.generate_query_embedding(
            current_message
        )
        
        results = await self.vector_service.similarity_search_user_history(
            query_embedding=query_embedding,
            user_id=user_id,
            k=k,
            entity_types=[HistoryEntityType.chat_message],
            threshold=0.5  # Higher threshold for conversation relevance
        )
        
        return [
            HistoryChunk(
                content=r["content"],
                entity_type=r["entity_type"],
                entity_id=r["entity_id"],
                similarity=r["similarity"],
                metadata=r["metadata"],
                created_at=r["created_at"]
            )
            for r in results
        ]
    
    # ==================== Bulk Operations ====================
    
    async def reindex_user_history(self, user_id: uuid.UUID) -> Dict[str, int]:
        """
        Reindex all history for a user.
        
        Useful for rebuilding embeddings after model updates.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with counts of indexed items
        """
        stats = {"anomalies": 0, "correlations": 0}
        
        # Reindex anomalies
        anomaly_result = await self.db.execute(
            select(Anomaly).where(Anomaly.user_id == user_id)
        )
        anomalies = anomaly_result.scalars().all()
        
        for anomaly in anomalies:
            if await self.index_anomaly(anomaly):
                stats["anomalies"] += 1
        
        # Reindex correlations
        correlation_result = await self.db.execute(
            select(Correlation).where(Correlation.user_id == user_id)
        )
        correlations = correlation_result.scalars().all()
        
        for correlation in correlations:
            if await self.index_correlation(correlation):
                stats["correlations"] += 1
        
        await self.db.commit()
        return stats
    
    def format_history_for_prompt(
        self,
        chunks: List[HistoryChunk],
        max_tokens: int = 1500
    ) -> str:
        """
        Format history chunks for inclusion in LLM prompt.
        
        Args:
            chunks: List of history chunks
            max_tokens: Maximum tokens to include
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = ["YOUR HEALTH HISTORY:"]
        current_tokens = 50  # Estimate for header
        
        for chunk in chunks:
            chunk_text = chunk.to_context_string()
            chunk_tokens = self.embedding_service.count_tokens(chunk_text)
            
            if current_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            current_tokens += chunk_tokens
        
        return "\n\n".join(context_parts)
