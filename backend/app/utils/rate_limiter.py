"""
Rate Limiter for OpenAI API calls.

Provides:
- Semaphore-based concurrency control
- Token bucket rate limiting
- Exponential backoff for retries
"""

import asyncio
import time
from typing import TypeVar, Callable, Any
from functools import wraps
from dataclasses import dataclass

T = TypeVar('T')


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_concurrent: int = 3  # Max concurrent API calls
    requests_per_minute: int = 50  # Max requests per minute
    min_delay_between_calls: float = 0.1  # Minimum delay in seconds
    max_retries: int = 3  # Max retries on rate limit errors
    base_retry_delay: float = 1.0  # Base delay for exponential backoff


class OpenAIRateLimiter:
    """
    Rate limiter for OpenAI API calls.
    
    Uses a combination of:
    1. Semaphore to limit concurrent requests
    2. Token bucket to limit requests per minute
    3. Minimum delay between requests
    
    Example:
        limiter = OpenAIRateLimiter()
        
        async with limiter.acquire():
            result = await openai_api_call()
    """
    
    _instance = None
    _embeddings_instance = None
    _chat_instance = None
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._last_request_time = 0.0
        self._request_times: list[float] = []
        self._lock = asyncio.Lock()
    
    @classmethod
    def for_embeddings(cls) -> 'OpenAIRateLimiter':
        """Get singleton rate limiter for embeddings API."""
        if cls._embeddings_instance is None:
            # Embeddings have higher rate limits
            cls._embeddings_instance = cls(RateLimitConfig(
                max_concurrent=5,
                requests_per_minute=200,
                min_delay_between_calls=0.05
            ))
        return cls._embeddings_instance
    
    @classmethod
    def for_chat(cls) -> 'OpenAIRateLimiter':
        """Get singleton rate limiter for chat completions API."""
        if cls._chat_instance is None:
            # Chat completions have stricter rate limits
            cls._chat_instance = cls(RateLimitConfig(
                max_concurrent=3,
                requests_per_minute=50,
                min_delay_between_calls=0.2
            ))
        return cls._chat_instance
    
    @classmethod
    def reset_instances(cls):
        """Reset singleton instances (useful for testing)."""
        cls._instance = None
        cls._embeddings_instance = None
        cls._chat_instance = None
    
    async def acquire(self):
        """Context manager to acquire rate limit slot."""
        return _RateLimitContext(self)
    
    async def _wait_for_slot(self):
        """Wait for an available rate limit slot."""
        async with self._lock:
            now = time.time()
            
            # Clean up old request times (older than 1 minute)
            self._request_times = [
                t for t in self._request_times 
                if now - t < 60
            ]
            
            # Check if we've exceeded the per-minute limit
            if len(self._request_times) >= self.config.requests_per_minute:
                oldest = self._request_times[0]
                wait_time = 60 - (now - oldest) + 0.1  # Add small buffer
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # Ensure minimum delay between calls
            time_since_last = now - self._last_request_time
            if time_since_last < self.config.min_delay_between_calls:
                await asyncio.sleep(
                    self.config.min_delay_between_calls - time_since_last
                )
            
            # Record this request
            self._last_request_time = time.time()
            self._request_times.append(self._last_request_time)
    
    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a function with rate limiting and retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self._semaphore:
                    await self._wait_for_slot()
                    return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if '429' in error_str or 'rate limit' in error_str:
                    if attempt < self.config.max_retries:
                        # Exponential backoff with jitter
                        delay = self.config.base_retry_delay * (2 ** attempt)
                        jitter = delay * 0.1 * (asyncio.get_event_loop().time() % 1)
                        await asyncio.sleep(delay + jitter)
                        continue
                
                # For other errors, don't retry
                raise
        
        raise last_exception


class _RateLimitContext:
    """Context manager for rate limiting."""
    
    def __init__(self, limiter: OpenAIRateLimiter):
        self.limiter = limiter
    
    async def __aenter__(self):
        await self.limiter._semaphore.acquire()
        await self.limiter._wait_for_slot()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.limiter._semaphore.release()
        return False


async def run_with_concurrency_limit(
    tasks: list[Callable[[], Any]],
    max_concurrent: int = 3,
    delay_between: float = 0.1
) -> list[Any]:
    """
    Run multiple async tasks with concurrency limiting.
    
    Args:
        tasks: List of async callables
        max_concurrent: Maximum concurrent tasks
        delay_between: Delay between starting tasks
        
    Returns:
        List of results in same order as input tasks
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    results = [None] * len(tasks)
    
    async def run_task(index: int, task: Callable[[], Any]):
        async with semaphore:
            await asyncio.sleep(delay_between * index / max_concurrent)
            results[index] = await task()
    
    await asyncio.gather(*[
        run_task(i, task) for i, task in enumerate(tasks)
    ])
    
    return results


async def run_in_batches(
    items: list[Any],
    batch_processor: Callable[[list[Any]], Any],
    batch_size: int = 10,
    delay_between_batches: float = 0.5
) -> list[Any]:
    """
    Process items in batches with delays between batches.
    
    Args:
        items: Items to process
        batch_processor: Async function that processes a batch
        batch_size: Size of each batch
        delay_between_batches: Delay between batches in seconds
        
    Returns:
        Combined results from all batches
    """
    all_results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        results = await batch_processor(batch)
        all_results.extend(results if isinstance(results, list) else [results])
        
        # Delay before next batch (except for last batch)
        if i + batch_size < len(items):
            await asyncio.sleep(delay_between_batches)
    
    return all_results
