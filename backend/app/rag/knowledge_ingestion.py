"""
Knowledge Ingestion Pipeline for indexing health knowledge.

Handles:
- Curated markdown files from local knowledge base
- PubMed research article abstracts
- MedlinePlus consumer health information
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embedding_service import EmbeddingService
from app.rag.vector_service import VectorService
from app.rag.external_apis.pubmed_client import PubMedClient, PubMedArticle
from app.rag.external_apis.medlineplus_client import MedlinePlusClient, HealthTopic
from app.utils.enums import KnowledgeSourceType
from app.config import settings


class KnowledgeIngestionPipeline:
    """
    Ingests and indexes health knowledge from multiple sources.
    
    Sources:
    - Curated markdown files (local knowledge base)
    - PubMed research abstracts (external API)
    - MedlinePlus health topics (external API)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService(db)
        self.pubmed_client = PubMedClient()
        self.medlineplus_client = MedlinePlusClient()
    
    async def close(self):
        """Close external API clients."""
        await self.pubmed_client.close()
        await self.medlineplus_client.close()
    
    # ==================== Markdown Ingestion ====================
    
    async def ingest_markdown_directory(
        self, 
        directory: Path,
        recursive: bool = True
    ) -> Dict[str, int]:
        """
        Ingest all markdown files from a directory.
        
        Args:
            directory: Path to directory containing markdown files
            recursive: Whether to search subdirectories
            
        Returns:
            Dict with counts of files processed, chunks created
        """
        if not directory.exists():
            raise ValueError(f"Directory not found: {directory}")
        
        pattern = "**/*.md" if recursive else "*.md"
        md_files = list(directory.glob(pattern))
        
        stats = {"files_processed": 0, "chunks_created": 0, "errors": 0}
        
        for md_file in md_files:
            try:
                # Extract metadata from path
                relative_path = md_file.relative_to(directory)
                category = relative_path.parent.as_posix() if relative_path.parent != Path(".") else "general"
                
                metadata = {
                    "file_path": str(relative_path),
                    "category": category,
                    "file_name": md_file.stem,
                }
                
                chunks_created = await self.ingest_markdown_file(md_file, metadata)
                stats["files_processed"] += 1
                stats["chunks_created"] += chunks_created
                
            except Exception as e:
                print(f"Error processing {md_file}: {e}")
                stats["errors"] += 1
        
        await self.db.commit()
        return stats
    
    async def ingest_markdown_file(
        self, 
        file_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Ingest a single markdown file.
        
        Args:
            file_path: Path to markdown file
            metadata: Additional metadata to store
            
        Returns:
            Number of chunks created
        """
        content = file_path.read_text(encoding="utf-8")
        
        # Extract title from first heading or filename
        title = self._extract_title(content) or file_path.stem.replace("_", " ").title()
        
        # Use file path as source_id for deduplication
        source_id = str(file_path)
        
        # Delete existing embeddings for this file (for re-indexing)
        await self.vector_service.delete_knowledge_embeddings(
            source_type=KnowledgeSourceType.curated,
            source_id=source_id
        )
        
        # Chunk the content
        chunks = self.embedding_service.chunk_text(content)
        
        # Generate embeddings in batch
        embeddings = await self.embedding_service.generate_embeddings_batch(chunks)
        
        # Store each chunk
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_metadata = {
                **(metadata or {}),
                "title": title,
                "total_chunks": len(chunks),
            }
            
            await self.vector_service.upsert_knowledge_embedding(
                content=chunk,
                embedding=embedding,
                source_type=KnowledgeSourceType.curated,
                source_id=source_id,
                title=title if i == 0 else f"{title} (Part {i + 1})",
                metadata=chunk_metadata,
                chunk_index=i
            )
        
        return len(chunks)
    
    def _extract_title(self, markdown_content: str) -> Optional[str]:
        """Extract title from markdown heading."""
        lines = markdown_content.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return None
    
    # ==================== PubMed Ingestion ====================
    
    async def ingest_pubmed_articles(
        self, 
        query: str, 
        max_results: int = 100
    ) -> Dict[str, int]:
        """
        Ingest PubMed articles for a search query.
        
        Args:
            query: PubMed search query
            max_results: Maximum articles to fetch
            
        Returns:
            Dict with counts
        """
        articles = await self.pubmed_client.search_and_fetch(query, max_results)
        
        stats = {"articles_fetched": len(articles), "chunks_created": 0}
        
        for article in articles:
            if not article.abstract:
                continue
            
            chunks_created = await self._index_pubmed_article(article)
            stats["chunks_created"] += chunks_created
        
        await self.db.commit()
        return stats
    
    async def _index_pubmed_article(self, article: PubMedArticle) -> int:
        """Index a single PubMed article."""
        source_id = f"PMID:{article.pmid}"
        
        # Delete existing (for re-indexing)
        await self.vector_service.delete_knowledge_embeddings(
            source_type=KnowledgeSourceType.pubmed,
            source_id=source_id
        )
        
        # Create text content
        content = article.to_text()
        
        # Check if content needs chunking
        chunks = self.embedding_service.chunk_text(content)
        embeddings = await self.embedding_service.generate_embeddings_batch(chunks)
        
        metadata = {
            "pmid": article.pmid,
            "journal": article.journal,
            "pub_date": article.pub_date,
            "authors": article.authors[:5],  # Limit authors stored
            "keywords": article.keywords,
            "mesh_terms": article.mesh_terms[:10],
            "doi": article.doi,
        }
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            await self.vector_service.upsert_knowledge_embedding(
                content=chunk,
                embedding=embedding,
                source_type=KnowledgeSourceType.pubmed,
                source_id=source_id,
                title=article.title,
                metadata=metadata,
                chunk_index=i
            )
        
        return len(chunks)
    
    async def ingest_pubmed_health_topics(
        self,
        topics: Optional[List[str]] = None,
        max_per_topic: int = 20
    ) -> Dict[str, int]:
        """
        Ingest PubMed articles for predefined health topics.
        
        Args:
            topics: List of topics or None for all predefined
            max_per_topic: Max articles per topic
            
        Returns:
            Dict with counts per topic
        """
        results = await self.pubmed_client.fetch_health_articles(topics, max_per_topic)
        
        stats = {"total_articles": 0, "total_chunks": 0, "by_topic": {}}
        
        for topic, articles in results.items():
            topic_stats = {"articles": len(articles), "chunks": 0}
            
            for article in articles:
                if article.abstract:
                    chunks = await self._index_pubmed_article(article)
                    topic_stats["chunks"] += chunks
            
            stats["by_topic"][topic] = topic_stats
            stats["total_articles"] += topic_stats["articles"]
            stats["total_chunks"] += topic_stats["chunks"]
        
        await self.db.commit()
        return stats
    
    # ==================== MedlinePlus Ingestion ====================
    
    async def ingest_medlineplus_topics(
        self, 
        topics: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Ingest MedlinePlus health topics.
        
        Args:
            topics: List of topic names or None for predefined
            
        Returns:
            Dict with counts
        """
        health_topics = await self.medlineplus_client.get_health_topics(topics)
        
        stats = {"topics_fetched": len(health_topics), "chunks_created": 0}
        
        for topic in health_topics:
            if not topic.summary:
                continue
            
            chunks_created = await self._index_medlineplus_topic(topic)
            stats["chunks_created"] += chunks_created
        
        await self.db.commit()
        return stats
    
    async def _index_medlineplus_topic(self, topic: HealthTopic) -> int:
        """Index a single MedlinePlus topic."""
        source_id = f"medlineplus:{topic.topic_id}"
        
        # Delete existing
        await self.vector_service.delete_knowledge_embeddings(
            source_type=KnowledgeSourceType.medlineplus,
            source_id=source_id
        )
        
        # Create text content
        content = topic.to_text()
        
        # Typically MedlinePlus topics are shorter, but chunk if needed
        chunks = self.embedding_service.chunk_text(content)
        embeddings = await self.embedding_service.generate_embeddings_batch(chunks)
        
        metadata = {
            "url": topic.url,
            "category": topic.primary_category,
            "aliases": topic.aliases,
            "related_topics": topic.related_topics,
        }
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            await self.vector_service.upsert_knowledge_embedding(
                content=chunk,
                embedding=embedding,
                source_type=KnowledgeSourceType.medlineplus,
                source_id=source_id,
                title=topic.title,
                metadata=metadata,
                chunk_index=i
            )
        
        return len(chunks)
    
    # ==================== Full Refresh ====================
    
    async def refresh_external_sources(
        self,
        include_pubmed: bool = True,
        include_medlineplus: bool = True,
        pubmed_max_per_topic: int = 20
    ) -> Dict[str, Any]:
        """
        Refresh all external knowledge sources.
        
        This can be run periodically (e.g., weekly) to update
        the knowledge base with new research.
        
        Args:
            include_pubmed: Whether to refresh PubMed
            include_medlineplus: Whether to refresh MedlinePlus
            pubmed_max_per_topic: Max PubMed articles per topic
            
        Returns:
            Combined stats from all sources
        """
        stats = {
            "started_at": datetime.utcnow().isoformat(),
            "pubmed": None,
            "medlineplus": None,
        }
        
        if include_pubmed:
            print("Refreshing PubMed articles...")
            stats["pubmed"] = await self.ingest_pubmed_health_topics(
                max_per_topic=pubmed_max_per_topic
            )
        
        if include_medlineplus:
            print("Refreshing MedlinePlus topics...")
            stats["medlineplus"] = await self.ingest_medlineplus_topics()
        
        stats["completed_at"] = datetime.utcnow().isoformat()
        
        return stats
    
    async def get_ingestion_stats(self) -> Dict[str, int]:
        """Get current counts of indexed knowledge."""
        return {
            "curated": await self.vector_service.count_knowledge_embeddings(
                KnowledgeSourceType.curated
            ),
            "pubmed": await self.vector_service.count_knowledge_embeddings(
                KnowledgeSourceType.pubmed
            ),
            "medlineplus": await self.vector_service.count_knowledge_embeddings(
                KnowledgeSourceType.medlineplus
            ),
        }
