"""Pydantic schemas for RAG operations."""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from uuid import UUID


class KnowledgeChunkResponse(BaseModel):
    """Schema for a knowledge chunk."""
    content: str
    source_type: str
    source_id: Optional[str]
    title: Optional[str]
    similarity: float
    metadata: Optional[Dict[str, Any]] = None


class RetrievalResult(BaseModel):
    """Schema for retrieval results."""
    query: str
    chunks: List[KnowledgeChunkResponse]
    total_chunks: int


class IngestionStats(BaseModel):
    """Schema for ingestion statistics."""
    files_processed: Optional[int] = None
    chunks_created: int
    errors: Optional[int] = None
    source_type: str


class KnowledgeBaseStats(BaseModel):
    """Schema for knowledge base statistics."""
    curated: int
    pubmed: int
    medlineplus: int
    total: int


class UserHistoryStats(BaseModel):
    """Schema for user history statistics."""
    anomalies: int
    correlations: int
    insights: int
    chat_messages: int
    total: int
