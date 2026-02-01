# VitalIQ RAG (Retrieval-Augmented Generation) Module
"""
This module provides RAG capabilities for VitalIQ:
- Health Knowledge Base retrieval
- User History retrieval
- Conversational chat with RAG context

Usage:
    from app.rag import HealthKnowledgeRAG, UserHistoryRAG
    
    # Initialize with database session
    health_rag = HealthKnowledgeRAG(db)
    user_rag = UserHistoryRAG(db)
    
    # Retrieve context for anomaly explanation
    context = await health_rag.retrieve_for_anomaly(anomaly)
    
    # Retrieve user's past similar patterns
    history = await user_rag.retrieve_similar_anomalies(user_id, anomaly)
"""

# Core services (lazy imports to avoid circular dependencies)
def get_embedding_service():
    from app.rag.embedding_service import EmbeddingService
    return EmbeddingService


def get_vector_service():
    from app.rag.vector_service import VectorService
    return VectorService


def get_health_knowledge_rag():
    from app.rag.health_knowledge_rag import HealthKnowledgeRAG
    return HealthKnowledgeRAG


def get_user_history_rag():
    from app.rag.user_history_rag import UserHistoryRAG
    return UserHistoryRAG


def get_knowledge_ingestion_pipeline():
    from app.rag.knowledge_ingestion import KnowledgeIngestionPipeline
    return KnowledgeIngestionPipeline


def get_prompt_builder():
    from app.rag.prompt_builder import RAGPromptBuilder
    return RAGPromptBuilder


# Direct exports for backward compatibility
__all__ = [
    "get_embedding_service",
    "get_vector_service",
    "get_health_knowledge_rag",
    "get_user_history_rag",
    "get_knowledge_ingestion_pipeline",
    "get_prompt_builder",
]
