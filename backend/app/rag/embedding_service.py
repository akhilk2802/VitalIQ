"""
Embedding Service for generating vector embeddings using OpenAI.

Uses text-embedding-3-large model (3072 dimensions) for high-quality
semantic representations of health knowledge and user history.

Includes rate limiting to prevent API throttling.
"""

import asyncio
import tiktoken
from typing import List, Optional
from openai import AsyncOpenAI

from app.config import settings
from app.utils.rate_limiter import OpenAIRateLimiter


class EmbeddingService:
    """Service for generating and managing text embeddings with rate limiting."""
    
    MODEL = settings.OPENAI_EMBEDDING_MODEL  # "text-embedding-3-large"
    DIMENSIONS = settings.EMBEDDING_DIMENSIONS  # 3072
    MAX_TOKENS = 8191  # Max tokens for text-embedding-3-large
    
    # Batch processing settings
    DEFAULT_BATCH_SIZE = 50  # Texts per API call (max 2048, but smaller is safer)
    DELAY_BETWEEN_BATCHES = 0.2  # Seconds between batch API calls
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self._tokenizer = None
        self._rate_limiter = OpenAIRateLimiter.for_embeddings()
    
    @property
    def tokenizer(self):
        """Lazy load tokenizer."""
        if self._tokenizer is None:
            self._tokenizer = tiktoken.encoding_for_model("gpt-4")  # Compatible encoding
        return self._tokenizer
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text with rate limiting.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            ValueError: If OpenAI API key is not configured
            Exception: If API call fails
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        # Truncate if too long
        text = self._truncate_text(text)
        
        async def _call():
            response = await self.client.embeddings.create(
                model=self.MODEL,
                input=text,
                dimensions=self.DIMENSIONS
            )
            return response.data[0].embedding
        
        return await self._rate_limiter.execute_with_retry(_call)
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str],
        batch_size: int = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches with rate limiting.
        
        This is more efficient than calling generate_embedding() for each text
        as it batches multiple texts into single API calls.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (default: 50)
            
        Returns:
            List of embedding vectors in same order as input texts
        """
        if not self.client:
            raise ValueError("OpenAI API key not configured")
        
        if not texts:
            return []
        
        batch_size = batch_size or self.DEFAULT_BATCH_SIZE
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Truncate each text in batch
            batch = [self._truncate_text(t) for t in batch]
            
            async def _call(batch_texts=batch):
                response = await self.client.embeddings.create(
                    model=self.MODEL,
                    input=batch_texts,
                    dimensions=self.DIMENSIONS
                )
                # Sort by index to maintain order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                return [item.embedding for item in sorted_data]
            
            batch_embeddings = await self._rate_limiter.execute_with_retry(_call)
            all_embeddings.extend(batch_embeddings)
            
            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(texts):
                await asyncio.sleep(self.DELAY_BETWEEN_BATCHES)
        
        return all_embeddings
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = None,
        chunk_overlap: int = None
    ) -> List[str]:
        """
        Split text into chunks for embedding.
        
        Uses tiktoken for accurate token counting and splits on
        sentence boundaries when possible.
        
        Args:
            text: Text to chunk
            chunk_size: Target tokens per chunk (default from settings)
            chunk_overlap: Overlap tokens between chunks (default from settings)
            
        Returns:
            List of text chunks
        """
        chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        chunk_overlap = chunk_overlap or settings.RAG_CHUNK_OVERLAP
        
        # Tokenize the text
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Get chunk tokens
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            # Try to find a good break point (sentence boundary)
            if end < len(tokens):
                # Look for sentence endings in the last 20% of the chunk
                search_start = int(len(chunk_text) * 0.8)
                last_period = chunk_text.rfind('. ', search_start)
                last_newline = chunk_text.rfind('\n', search_start)
                
                break_point = max(last_period, last_newline)
                if break_point > search_start:
                    chunk_text = chunk_text[:break_point + 1]
                    # Recalculate end position based on actual chunk
                    chunk_tokens = self.tokenizer.encode(chunk_text)
                    end = start + len(chunk_tokens)
            
            chunks.append(chunk_text.strip())
            
            # Move start position with overlap
            start = end - chunk_overlap
            if start <= chunks[-1] if chunks else 0:
                start = end  # Prevent infinite loop
        
        return chunks
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))
    
    def _truncate_text(self, text: str) -> str:
        """Truncate text to max tokens if needed."""
        tokens = self.tokenizer.encode(text)
        if len(tokens) > self.MAX_TOKENS:
            tokens = tokens[:self.MAX_TOKENS]
            text = self.tokenizer.decode(tokens)
        return text
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.
        
        This is a convenience wrapper that handles query-specific processing.
        
        Args:
            query: Search query text
            
        Returns:
            Embedding vector for the query
        """
        # For queries, we might want to add prefixes or process differently
        # For now, same as regular embedding
        return await self.generate_embedding(query)
