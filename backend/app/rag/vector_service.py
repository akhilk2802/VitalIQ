"""
Vector Service for pgvector operations.

Provides low-level vector database operations including:
- Similarity search with cosine distance
- Embedding upsert and deletion
- Filtered queries
"""

import uuid
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text, and_
from sqlalchemy.dialects.postgresql import insert

from app.models.knowledge_embedding import KnowledgeEmbedding
from app.models.user_history_embedding import UserHistoryEmbedding
from app.utils.enums import KnowledgeSourceType, HistoryEntityType


class VectorService:
    """Low-level vector operations with pgvector."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def similarity_search_knowledge(
        self,
        query_embedding: List[float],
        k: int = 5,
        source_types: Optional[List[KnowledgeSourceType]] = None,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search knowledge embeddings by similarity.
        
        Args:
            query_embedding: Query vector
            k: Number of results to return
            source_types: Optional filter by source type
            threshold: Minimum similarity threshold (0-1, higher is more similar)
            
        Returns:
            List of dicts with content, metadata, and similarity score
        """
        # Build the query using pgvector cosine distance
        # Note: pgvector uses <=> for cosine distance (1 - cosine_similarity)
        # So we order ASC and convert distance to similarity
        
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # Base query with similarity calculation
        query = f"""
            SELECT 
                id,
                content,
                source_type,
                source_id,
                title,
                extra_metadata,
                chunk_index,
                created_at,
                1 - (embedding <=> '{embedding_str}'::vector) as similarity
            FROM knowledge_embeddings
            WHERE 1 - (embedding <=> '{embedding_str}'::vector) >= :threshold
        """
        
        params = {"threshold": threshold, "k": k}
        
        # Add source type filter
        if source_types:
            source_values = [st.value for st in source_types]
            query += " AND source_type = ANY(:source_types::text[])"
            params["source_types"] = source_values
        
        query += f" ORDER BY embedding <=> '{embedding_str}'::vector ASC LIMIT :k"
        
        try:
            result = await self.db.execute(text(query), params)
            rows = result.fetchall()
        except Exception as e:
            # Log and return empty on query failure
            print(f"Knowledge vector search query failed: {e}")
            return []
        
        return [
            {
                "id": str(row.id),
                "content": row.content,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "title": row.title,
                "metadata": row.extra_metadata,
                "chunk_index": row.chunk_index,
                "similarity": float(row.similarity),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    
    async def similarity_search_user_history(
        self,
        query_embedding: List[float],
        user_id: uuid.UUID,
        k: int = 5,
        entity_types: Optional[List[HistoryEntityType]] = None,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search user history embeddings by similarity.
        
        Args:
            query_embedding: Query vector
            user_id: User ID to filter by
            k: Number of results to return
            entity_types: Optional filter by entity type
            threshold: Minimum similarity threshold
            
        Returns:
            List of dicts with content, metadata, and similarity score
        """
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # Build query with proper casting for user_id
        query = f"""
            SELECT 
                id,
                user_id,
                content,
                entity_type,
                entity_id,
                extra_metadata,
                created_at,
                1 - (embedding <=> '{embedding_str}'::vector) as similarity
            FROM user_history_embeddings
            WHERE user_id = :user_id::uuid
            AND 1 - (embedding <=> '{embedding_str}'::vector) >= :threshold
        """
        
        # Pass user_id as string, cast in SQL
        params = {"user_id": str(user_id), "threshold": threshold, "k": k}
        
        if entity_types:
            entity_values = [et.value for et in entity_types]
            query += " AND entity_type = ANY(:entity_types::text[])"
            params["entity_types"] = entity_values
        
        query += f" ORDER BY embedding <=> '{embedding_str}'::vector ASC LIMIT :k"
        
        try:
            result = await self.db.execute(text(query), params)
            rows = result.fetchall()
        except Exception as e:
            # Log and return empty on query failure
            print(f"Vector search query failed: {e}")
            return []
        
        return [
            {
                "id": str(row.id),
                "user_id": str(row.user_id),
                "content": row.content,
                "entity_type": row.entity_type,
                "entity_id": str(row.entity_id) if row.entity_id else None,
                "metadata": row.extra_metadata,
                "similarity": float(row.similarity),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    
    async def upsert_knowledge_embedding(
        self,
        content: str,
        embedding: List[float],
        source_type: KnowledgeSourceType,
        source_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_index: Optional[int] = None
    ) -> uuid.UUID:
        """
        Insert or update a knowledge embedding.
        
        Args:
            content: Text content
            embedding: Embedding vector
            source_type: Source type (curated, pubmed, medlineplus)
            source_id: External source ID (file path, PMID, etc.)
            title: Document title
            metadata: Additional metadata
            chunk_index: Index for chunked documents
            
        Returns:
            ID of the created/updated embedding
        """
        embedding_id = uuid.uuid4()
        
        knowledge_embedding = KnowledgeEmbedding(
            id=embedding_id,
            content=content,
            embedding=embedding,
            source_type=source_type,
            source_id=source_id,
            title=title,
            metadata=metadata,
            chunk_index=chunk_index,
        )
        
        self.db.add(knowledge_embedding)
        await self.db.flush()
        
        return embedding_id
    
    async def upsert_user_history_embedding(
        self,
        user_id: uuid.UUID,
        content: str,
        embedding: List[float],
        entity_type: HistoryEntityType,
        entity_id: Optional[uuid.UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        """
        Insert or update a user history embedding.
        
        Args:
            user_id: User ID
            content: Text content
            embedding: Embedding vector
            entity_type: Type of entity (anomaly, correlation, etc.)
            entity_id: Reference to original entity
            metadata: Additional metadata
            
        Returns:
            ID of the created/updated embedding
        """
        embedding_id = uuid.uuid4()
        
        history_embedding = UserHistoryEmbedding(
            id=embedding_id,
            user_id=user_id,
            content=content,
            embedding=embedding,
            entity_type=entity_type,
            entity_id=entity_id,
            extra_metadata=metadata,
        )
        
        self.db.add(history_embedding)
        await self.db.flush()
        
        return embedding_id
    
    async def delete_knowledge_embeddings(
        self,
        source_type: Optional[KnowledgeSourceType] = None,
        source_id: Optional[str] = None
    ) -> int:
        """
        Delete knowledge embeddings by filter.
        
        Args:
            source_type: Filter by source type
            source_id: Filter by source ID
            
        Returns:
            Number of deleted embeddings
        """
        conditions = []
        
        if source_type:
            conditions.append(KnowledgeEmbedding.source_type == source_type)
        if source_id:
            conditions.append(KnowledgeEmbedding.source_id == source_id)
        
        if not conditions:
            return 0
        
        stmt = delete(KnowledgeEmbedding).where(and_(*conditions))
        result = await self.db.execute(stmt)
        
        return result.rowcount
    
    async def delete_user_history_embeddings(
        self,
        user_id: uuid.UUID,
        entity_type: Optional[HistoryEntityType] = None,
        entity_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Delete user history embeddings by filter.
        
        Args:
            user_id: User ID (required)
            entity_type: Filter by entity type
            entity_id: Filter by specific entity ID
            
        Returns:
            Number of deleted embeddings
        """
        conditions = [UserHistoryEmbedding.user_id == user_id]
        
        if entity_type:
            conditions.append(UserHistoryEmbedding.entity_type == entity_type)
        if entity_id:
            conditions.append(UserHistoryEmbedding.entity_id == entity_id)
        
        stmt = delete(UserHistoryEmbedding).where(and_(*conditions))
        result = await self.db.execute(stmt)
        
        return result.rowcount
    
    async def get_knowledge_embedding_by_source(
        self,
        source_type: KnowledgeSourceType,
        source_id: str
    ) -> Optional[KnowledgeEmbedding]:
        """Get knowledge embedding by source."""
        result = await self.db.execute(
            select(KnowledgeEmbedding).where(
                and_(
                    KnowledgeEmbedding.source_type == source_type,
                    KnowledgeEmbedding.source_id == source_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def count_knowledge_embeddings(
        self,
        source_type: Optional[KnowledgeSourceType] = None
    ) -> int:
        """Count knowledge embeddings."""
        from sqlalchemy import func
        
        query = select(func.count(KnowledgeEmbedding.id))
        if source_type:
            query = query.where(KnowledgeEmbedding.source_type == source_type)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def count_user_history_embeddings(
        self,
        user_id: uuid.UUID,
        entity_type: Optional[HistoryEntityType] = None
    ) -> int:
        """Count user history embeddings."""
        from sqlalchemy import func
        
        query = select(func.count(UserHistoryEmbedding.id)).where(
            UserHistoryEmbedding.user_id == user_id
        )
        if entity_type:
            query = query.where(UserHistoryEmbedding.entity_type == entity_type)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
