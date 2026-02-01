"""
RAG Management API Router.

Provides endpoints for:
- Knowledge base ingestion
- Index statistics
- Manual re-indexing of user history
"""

import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user
from app.rag.knowledge_ingestion import KnowledgeIngestionPipeline
from app.rag.user_history_rag import UserHistoryRAG
from app.services.anomaly_service import AnomalyService
from app.services.correlation_service import CorrelationService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


class IngestionResponse(BaseModel):
    """Response for ingestion operations."""
    status: str
    message: str
    stats: Optional[dict] = None


class IndexStats(BaseModel):
    """Current index statistics."""
    knowledge_base: dict
    user_history: dict


# ==================== Knowledge Base Management ====================

@router.post("/knowledge/ingest", response_model=IngestionResponse)
async def ingest_knowledge_base(
    include_curated: bool = True,
    include_pubmed: bool = False,  # Disabled by default (requires API)
    include_medlineplus: bool = False,  # Disabled by default
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest health knowledge into the vector database.
    
    - **include_curated**: Ingest local markdown files from knowledge_base/
    - **include_pubmed**: Fetch and ingest PubMed research articles
    - **include_medlineplus**: Fetch and ingest MedlinePlus topics
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured. RAG requires embeddings."
        )
    
    pipeline = KnowledgeIngestionPipeline(db)
    stats = {}
    
    try:
        if include_curated:
            # Ingest local knowledge base
            kb_path = Path(__file__).parent.parent.parent / "knowledge_base"
            if kb_path.exists():
                logger.info(f"Ingesting markdown files from {kb_path}")
                stats["curated"] = await pipeline.ingest_markdown_directory(kb_path)
            else:
                stats["curated"] = {"error": f"Knowledge base directory not found: {kb_path}"}
        
        if include_pubmed:
            logger.info("Ingesting PubMed articles...")
            stats["pubmed"] = await pipeline.ingest_pubmed_health_topics(max_per_topic=10)
        
        if include_medlineplus:
            logger.info("Ingesting MedlinePlus topics...")
            stats["medlineplus"] = await pipeline.ingest_medlineplus_topics()
        
        await db.commit()
        
        return IngestionResponse(
            status="success",
            message="Knowledge base ingested successfully",
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Knowledge ingestion failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )
    finally:
        await pipeline.close()


@router.get("/knowledge/stats", response_model=dict)
async def get_knowledge_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about the indexed knowledge base.
    """
    pipeline = KnowledgeIngestionPipeline(db)
    try:
        stats = await pipeline.get_ingestion_stats()
        total = sum(stats.values())
        return {
            "total_chunks": total,
            "by_source": stats,
            "status": "ready" if total > 0 else "empty"
        }
    finally:
        await pipeline.close()


# ==================== User History Management ====================

@router.post("/user-history/reindex", response_model=IngestionResponse)
async def reindex_user_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Re-index the current user's anomalies and correlations for RAG retrieval.
    
    This is useful if indexing failed previously or after bulk data import.
    """
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI API key not configured. RAG requires embeddings."
        )
    
    user_rag = UserHistoryRAG(db)
    anomaly_service = AnomalyService(db)
    correlation_service = CorrelationService(db)
    
    stats = {
        "anomalies_indexed": 0,
        "correlations_indexed": 0,
        "errors": []
    }
    
    try:
        # Get all user anomalies
        anomalies = await anomaly_service.get_recent_anomalies(
            user_id=current_user.id,
            limit=500  # Index up to 500 recent anomalies
        )
        
        for anomaly in anomalies:
            try:
                await user_rag.index_anomaly(anomaly)
                stats["anomalies_indexed"] += 1
            except Exception as e:
                stats["errors"].append(f"Anomaly {anomaly.id}: {str(e)}")
                logger.warning(f"Failed to index anomaly {anomaly.id}: {e}")
        
        # Get all user correlations
        correlations = await correlation_service.get_correlations(
            user_id=current_user.id,
            limit=200
        )
        
        for correlation in correlations:
            try:
                await user_rag.index_correlation(correlation)
                stats["correlations_indexed"] += 1
            except Exception as e:
                stats["errors"].append(f"Correlation {correlation.id}: {str(e)}")
                logger.warning(f"Failed to index correlation {correlation.id}: {e}")
        
        await db.commit()
        
        return IngestionResponse(
            status="success",
            message=f"Indexed {stats['anomalies_indexed']} anomalies and {stats['correlations_indexed']} correlations",
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"User history reindex failed: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reindex failed: {str(e)}"
        )


@router.get("/user-history/stats", response_model=dict)
async def get_user_history_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics about the user's indexed history.
    """
    from app.rag.vector_service import VectorService
    
    vector_service = VectorService(db)
    
    try:
        count = await vector_service.count_user_history_embeddings(current_user.id)
        return {
            "user_id": str(current_user.id),
            "total_embeddings": count,
            "status": "ready" if count > 0 else "empty"
        }
    except Exception as e:
        logger.error(f"Failed to get user history stats: {e}")
        return {
            "user_id": str(current_user.id),
            "total_embeddings": 0,
            "status": "error",
            "error": str(e)
        }


# ==================== Debug/Status ====================

@router.get("/status")
async def get_rag_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall RAG system status.
    """
    from app.rag.vector_service import VectorService
    
    status_info = {
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
        "embedding_dimensions": settings.EMBEDDING_DIMENSIONS,
    }
    
    if settings.OPENAI_API_KEY:
        pipeline = KnowledgeIngestionPipeline(db)
        vector_service = VectorService(db)
        
        try:
            knowledge_stats = await pipeline.get_ingestion_stats()
            user_history_count = await vector_service.count_user_history_embeddings(current_user.id)
            
            status_info["knowledge_base"] = {
                "total_chunks": sum(knowledge_stats.values()),
                "by_source": knowledge_stats
            }
            status_info["user_history"] = {
                "total_embeddings": user_history_count
            }
            status_info["ready"] = sum(knowledge_stats.values()) > 0
        except Exception as e:
            status_info["error"] = str(e)
            status_info["ready"] = False
        finally:
            await pipeline.close()
    else:
        status_info["ready"] = False
        status_info["message"] = "OpenAI API key not configured"
    
    return status_info
