"""
Health Knowledge RAG Service for retrieving relevant health information.

Provides context for:
- Anomaly explanations
- Correlation insights  
- Chat responses
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embedding_service import EmbeddingService
from app.rag.vector_service import VectorService
from app.utils.enums import KnowledgeSourceType
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.config import settings


@dataclass
class KnowledgeChunk:
    """Represents a retrieved knowledge chunk."""
    content: str
    source_type: str
    source_id: Optional[str]
    title: Optional[str]
    similarity: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_context_string(self) -> str:
        """Format as context string for LLM prompt."""
        source_label = self._get_source_label()
        
        parts = []
        if self.title:
            parts.append(f"[{source_label}: {self.title}]")
        else:
            parts.append(f"[{source_label}]")
        parts.append(self.content)
        
        return "\n".join(parts)
    
    def _get_source_label(self) -> str:
        """Get human-readable source label."""
        labels = {
            "curated": "Health Guide",
            "pubmed": "Research",
            "medlineplus": "MedlinePlus",
        }
        return labels.get(self.source_type, self.source_type.title())


class HealthKnowledgeRAG:
    """
    RAG service for health knowledge retrieval.
    
    Retrieves relevant health information from:
    - Curated knowledge base (markdown files)
    - PubMed research abstracts
    - MedlinePlus consumer health information
    """
    
    # Metric name to search query mappings
    METRIC_QUERIES = {
        # Sleep metrics
        "sleep_hours": "sleep duration health effects",
        "sleep_quality": "sleep quality factors and health",
        "awakenings": "sleep interruptions wake patterns health",
        
        # Heart metrics
        "resting_hr": "resting heart rate health cardiovascular",
        "hrv": "heart rate variability HRV stress recovery",
        "bp_systolic": "blood pressure systolic hypertension",
        "bp_diastolic": "blood pressure diastolic health",
        
        # Nutrition metrics
        "total_calories": "caloric intake energy balance",
        "total_protein_g": "protein intake health benefits",
        "total_carbs_g": "carbohydrates nutrition blood sugar",
        "total_sugar_g": "sugar intake health effects",
        "total_fats_g": "dietary fat health nutrition",
        
        # Exercise metrics
        "exercise_minutes": "physical activity exercise health benefits",
        "exercise_calories": "exercise energy expenditure calories",
        "exercise_intensity_avg": "exercise intensity training",
        
        # Body metrics
        "weight_kg": "body weight management health",
        "body_fat_pct": "body fat percentage composition health",
        
        # Chronic metrics
        "blood_glucose_fasting": "fasting blood glucose diabetes",
        "blood_glucose_post_meal": "postprandial blood sugar glucose",
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService(db)
    
    async def retrieve(
        self,
        query: str,
        metrics: Optional[List[str]] = None,
        source_types: Optional[List[KnowledgeSourceType]] = None,
        k: int = None
    ) -> List[KnowledgeChunk]:
        """
        Retrieve relevant health knowledge for a query.
        
        Args:
            query: Search query
            metrics: Optional list of metric names to enhance query
            source_types: Optional filter by source types
            k: Number of results (default from settings)
            
        Returns:
            List of KnowledgeChunk objects
        """
        k = k or settings.RAG_TOP_K
        
        # Enhance query with metric context if provided
        enhanced_query = self._enhance_query(query, metrics)
        
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_query_embedding(
            enhanced_query
        )
        
        # Search knowledge base
        results = await self.vector_service.similarity_search_knowledge(
            query_embedding=query_embedding,
            k=k,
            source_types=source_types,
            threshold=0.3  # Minimum similarity threshold
        )
        
        return [
            KnowledgeChunk(
                content=r["content"],
                source_type=r["source_type"],
                source_id=r["source_id"],
                title=r["title"],
                similarity=r["similarity"],
                metadata=r["metadata"]
            )
            for r in results
        ]
    
    def _enhance_query(
        self, 
        query: str, 
        metrics: Optional[List[str]] = None
    ) -> str:
        """Enhance query with metric-specific context."""
        if not metrics:
            return query
        
        # Add metric-specific terms to query
        metric_terms = []
        for metric in metrics:
            if metric in self.METRIC_QUERIES:
                metric_terms.append(self.METRIC_QUERIES[metric])
        
        if metric_terms:
            return f"{query}. Related: {' '.join(metric_terms)}"
        
        return query
    
    async def retrieve_for_anomaly(
        self, 
        anomaly: Anomaly,
        k: int = 3
    ) -> str:
        """
        Retrieve context for explaining an anomaly.
        
        Args:
            anomaly: Anomaly object
            k: Number of chunks to retrieve
            
        Returns:
            Formatted context string for LLM prompt
        """
        # Build query based on anomaly
        metric_name = anomaly.metric_name.replace("_", " ")
        direction = "elevated" if anomaly.metric_value > anomaly.baseline_value else "low"
        
        query = f"{direction} {metric_name} health implications causes"
        
        chunks = await self.retrieve(
            query=query,
            metrics=[anomaly.metric_name],
            k=k
        )
        
        if not chunks:
            return ""
        
        # Format as context
        context_parts = ["HEALTH KNOWLEDGE CONTEXT:"]
        for chunk in chunks:
            context_parts.append(chunk.to_context_string())
            context_parts.append("")  # Empty line separator
        
        return "\n".join(context_parts)
    
    async def retrieve_for_correlation(
        self, 
        correlation: Correlation,
        k: int = 3
    ) -> str:
        """
        Retrieve context for explaining a correlation.
        
        Args:
            correlation: Correlation object
            k: Number of chunks to retrieve
            
        Returns:
            Formatted context string for LLM prompt
        """
        metric_a = correlation.metric_a.replace("_", " ")
        metric_b = correlation.metric_b.replace("_", " ")
        
        # Build query based on correlation type
        direction = "positive" if correlation.correlation_value > 0 else "negative"
        
        if correlation.lag_days > 0:
            query = f"relationship between {metric_a} and {metric_b} delayed effect"
        elif correlation.causal_direction:
            query = f"how {metric_a} affects {metric_b} causal relationship"
        else:
            query = f"{direction} correlation between {metric_a} and {metric_b}"
        
        chunks = await self.retrieve(
            query=query,
            metrics=[correlation.metric_a, correlation.metric_b],
            k=k
        )
        
        if not chunks:
            return ""
        
        context_parts = ["HEALTH KNOWLEDGE CONTEXT:"]
        for chunk in chunks:
            context_parts.append(chunk.to_context_string())
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    async def retrieve_for_metrics(
        self,
        metrics: List[str],
        k: int = 5
    ) -> str:
        """
        Retrieve general context for a set of metrics.
        
        Useful for chat responses when user asks about their data.
        
        Args:
            metrics: List of metric names
            k: Number of chunks to retrieve
            
        Returns:
            Formatted context string
        """
        if not metrics:
            return ""
        
        # Build query from metric names
        metric_terms = [m.replace("_", " ") for m in metrics]
        query = f"health information about {', '.join(metric_terms)}"
        
        chunks = await self.retrieve(
            query=query,
            metrics=metrics,
            k=k
        )
        
        if not chunks:
            return ""
        
        context_parts = ["RELEVANT HEALTH KNOWLEDGE:"]
        for chunk in chunks:
            context_parts.append(chunk.to_context_string())
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    async def retrieve_for_chat(
        self,
        user_message: str,
        recent_metrics: Optional[List[str]] = None,
        k: int = 4
    ) -> List[KnowledgeChunk]:
        """
        Retrieve context for a chat message.
        
        Args:
            user_message: User's chat message
            recent_metrics: Metrics the user has recent data for
            k: Number of chunks to retrieve
            
        Returns:
            List of KnowledgeChunk objects
        """
        # Extract potential metrics from user message
        detected_metrics = self._detect_metrics_in_text(user_message)
        
        # Combine with recent metrics
        all_metrics = list(set((detected_metrics or []) + (recent_metrics or [])))
        
        return await self.retrieve(
            query=user_message,
            metrics=all_metrics if all_metrics else None,
            k=k
        )
    
    def _detect_metrics_in_text(self, text: str) -> List[str]:
        """Detect metric references in text."""
        text_lower = text.lower()
        detected = []
        
        # Keyword to metric mapping
        keyword_map = {
            "sleep": ["sleep_hours", "sleep_quality"],
            "heart rate": ["resting_hr"],
            "hrv": ["hrv"],
            "blood pressure": ["bp_systolic", "bp_diastolic"],
            "exercise": ["exercise_minutes", "exercise_calories"],
            "calories": ["total_calories"],
            "weight": ["weight_kg"],
            "glucose": ["blood_glucose_fasting"],
            "sugar": ["total_sugar_g", "blood_glucose_fasting"],
            "protein": ["total_protein_g"],
            "carbs": ["total_carbs_g"],
        }
        
        for keyword, metrics in keyword_map.items():
            if keyword in text_lower:
                detected.extend(metrics)
        
        return list(set(detected))
    
    def format_chunks_for_prompt(
        self, 
        chunks: List[KnowledgeChunk],
        max_tokens: int = 2000
    ) -> str:
        """
        Format chunks for inclusion in LLM prompt.
        
        Handles token limits and formatting.
        
        Args:
            chunks: List of KnowledgeChunk objects
            max_tokens: Maximum tokens for context
            
        Returns:
            Formatted context string
        """
        if not chunks:
            return ""
        
        context_parts = []
        current_tokens = 0
        
        for chunk in chunks:
            chunk_text = chunk.to_context_string()
            chunk_tokens = self.embedding_service.count_tokens(chunk_text)
            
            if current_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(chunk_text)
            current_tokens += chunk_tokens
        
        return "\n\n".join(context_parts)
