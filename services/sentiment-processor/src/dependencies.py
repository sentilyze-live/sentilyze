"""FastAPI dependency injection for Semantic Cache and Knowledge Graph.

This module provides dependency injection setup for FastAPI to use
the new semantic cache and knowledge graph features in the sentiment
processor service.

Usage:
    >>> from fastapi import FastAPI, Depends
    >>> from .dependencies import get_semantic_cache, get_knowledge_graph
    >>> 
    >>> app = FastAPI()
    >>> 
    >>> @app.post("/analyze")
    ... async def analyze_text(
    ...     text: str,
    ...     semantic_cache: FirebaseSemanticCache = Depends(get_semantic_cache),
    ...     knowledge_graph: KnowledgeGraphBuilder = Depends(get_knowledge_graph),
    ... ):
    ...     # Check semantic cache
    ...     cached = await semantic_cache.get_similar(text)
    ...     if cached:
    ...         return cached
    ...     
    ...     # Call Gemini API
    ...     result = await call_gemini_api(text)
    ...     
    ...     # Store in semantic cache
    ...     await semantic_cache.store_result(text, result)
    ...     
    ...     # Update knowledge graph
    ...     await knowledge_graph.process_text(text, sentiment=result["score"])
    ...     
    ...     return result
"""

import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from fastapi import FastAPI, Request
from google.cloud import firestore, storage

if TYPE_CHECKING:
    # Optional ML deps live in the `ml` Poetry group.
    # We only import these for type checking to avoid hard runtime dependency.
    from semantic_cache import FirebaseSemanticCache  # pragma: no cover
    from knowledge_graph import KnowledgeGraphBuilder  # pragma: no cover

# Global instances (singleton pattern)
_semantic_cache: Optional["FirebaseSemanticCache"] = None
_knowledge_graph: Optional["KnowledgeGraphBuilder"] = None
_firestore_client: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    """Get or create Firestore client singleton."""
    global _firestore_client
    if _firestore_client is None:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "sentilyze-v5-clean")
        _firestore_client = firestore.Client(project=project_id)
    return _firestore_client


async def get_semantic_cache() -> AsyncGenerator[FirebaseSemanticCache, None]:
    """FastAPI dependency for semantic cache.
    
    Usage:
        >>> @app.post("/analyze")
        ... async def analyze(
        ...     text: str,
        ...     cache: FirebaseSemanticCache = Depends(get_semantic_cache)
        ... ):
        ...     result = await cache.get_similar(text)
        ...     ...
    """
    global _semantic_cache
    
    if _semantic_cache is None:
        try:
            from semantic_cache import FirebaseSemanticCache
        except ImportError as e:
            raise RuntimeError(
                "Semantic cache is unavailable (optional ML deps not installed). "
                "Install with: `poetry install --with ml`"
            ) from e

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "sentilyze-v5-clean")
        storage_bucket = os.getenv("CACHE_STORAGE_BUCKET", f"{project_id}-cache")
        
        _semantic_cache = FirebaseSemanticCache(
            firestore_client=get_firestore_client(),
            storage_bucket=storage_bucket,
            similarity_threshold=0.85,
            max_entries=10000,
        )
        await _semantic_cache.initialize()
    
    try:
        yield _semantic_cache
    except Exception:
        # Don't close on request error, only on shutdown
        pass


async def get_knowledge_graph() -> AsyncGenerator[KnowledgeGraphBuilder, None]:
    """FastAPI dependency for knowledge graph.
    
    Usage:
        >>> @app.post("/analyze")
        ... async def analyze(
        ...     text: str,
        ...     kg: KnowledgeGraphBuilder = Depends(get_knowledge_graph)
        ... ):
        ...     result = await kg.process_text(text)
        ...     ...
    """
    global _knowledge_graph
    
    if _knowledge_graph is None:
        try:
            from knowledge_graph import KnowledgeGraphBuilder
        except ImportError as e:
            raise RuntimeError(
                "Knowledge graph is unavailable (optional ML deps not installed). "
                "Install with: `poetry install --with ml`"
            ) from e

        _knowledge_graph = KnowledgeGraphBuilder(
            firestore_client=get_firestore_client(),
            collection="knowledge_graph",
        )
        await _knowledge_graph.initialize()
    
    try:
        yield _knowledge_graph
    except Exception:
        pass


async def shutdown_ml_services() -> None:
    """Shutdown all ML services gracefully.
    
    Call this during application shutdown to persist caches and graphs.
    """
    global _semantic_cache, _knowledge_graph
    
    if _semantic_cache:
        # Lazy import to keep ML deps optional.
        from semantic_cache import close_semantic_cache
        await close_semantic_cache()
        _semantic_cache = None
    
    if _knowledge_graph:
        # Lazy import to keep ML deps optional.
        from knowledge_graph import close_knowledge_graph
        await close_knowledge_graph()
        _knowledge_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown.
    
    Usage:
        >>> app = FastAPI(lifespan=lifespan)
    """
    # Startup: Initialize services
    print("🚀 Initializing ML services...")
    
    # Initialize semantic cache
    cache = await get_semantic_cache().__anext__()
    stats = await cache.get_cache_stats()
    print(f"✅ Semantic Cache: {stats['entry_count']} entries")
    
    # Initialize knowledge graph
    kg = await get_knowledge_graph().__anext__()
    print(f"✅ Knowledge Graph: {kg.graph.number_of_nodes()} nodes, {kg.graph.number_of_edges()} edges")
    
    print("🎯 All ML services ready!")
    
    yield
    
    # Shutdown: Persist caches
    print("🔄 Shutting down ML services...")
    await shutdown_ml_services()
    print("✅ ML services shutdown complete")


# Integration helper for existing analyzer
class MLServicesIntegration:
    """Helper class to integrate ML services with existing analyzer.
    
    This provides a clean interface for the existing UnifiedSentimentAnalyzer
to use semantic cache and knowledge graph without major refactoring.
    """
    
    def __init__(
        self,
        semantic_cache: Optional[FirebaseSemanticCache] = None,
        knowledge_graph: Optional[KnowledgeGraphBuilder] = None,
    ):
        self.semantic_cache = semantic_cache
        self.knowledge_graph = knowledge_graph
        self._cache_hits = 0
        self._cache_misses = 0
    
    async def analyze_with_cache(
        self,
        text: str,
        market_type: str = "generic",
        analyzer_func=None,
    ) -> dict:
        """Analyze text with semantic cache.
        
        Args:
            text: Text to analyze
            market_type: Market type (crypto, gold, generic)
            analyzer_func: Async function to call on cache miss
            
        Returns:
            Analysis result
        """
        if self.semantic_cache is None:
            # No cache, call analyzer directly
            if analyzer_func:
                return await analyzer_func(text)
            raise ValueError("No analyzer_func provided and no cache available")
        
        # Check cache
        cached_result = await self.semantic_cache.get_similar(text)
        
        if cached_result:
            self._cache_hits += 1
            print(f"🎯 Semantic Cache HIT ({self._cache_hits} total)")
            return cached_result
        
        # Cache miss - call analyzer
        self._cache_misses += 1
        print(f"📝 Semantic Cache MISS ({self._cache_misses} total)")
        
        if analyzer_func is None:
            raise ValueError("analyzer_func required for cache miss")
        
        result = await analyzer_func(text)
        
        # Store in cache
        await self.semantic_cache.store_result(text, result)
        
        return result
    
    async def update_knowledge_graph(
        self,
        text: str,
        sentiment: float = 0.0,
    ) -> None:
        """Update knowledge graph with analyzed text.
        
        Args:
            text: Analyzed text
            sentiment: Sentiment score (-1 to 1)
        """
        if self.knowledge_graph:
            await self.knowledge_graph.process_text(text, sentiment=sentiment)
    
    def get_stats(self) -> dict:
        """Get ML services statistics."""
        stats = {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": 0.0,
        }
        
        total = self._cache_hits + self._cache_misses
        if total > 0:
            stats["cache_hit_rate"] = self._cache_hits / total
        
        if self.knowledge_graph:
            stats["graph_nodes"] = self.knowledge_graph.graph.number_of_nodes()
            stats["graph_edges"] = self.knowledge_graph.graph.number_of_edges()
        
        return stats


# Convenience function for quick integration
def create_ml_integration(
    firestore_client: Optional[firestore.Client] = None,
    enable_cache: bool = True,
    enable_graph: bool = True,
) -> MLServicesIntegration:
    """Create ML services integration with proper initialization.
    
    This is a synchronous helper for use in synchronous contexts.
    For async contexts, use get_semantic_cache() and get_knowledge_graph().
    
    Args:
        firestore_client: Optional Firestore client
        enable_cache: Enable semantic cache
        enable_graph: Enable knowledge graph
        
    Returns:
        MLServicesIntegration instance (not initialized, call initialize_async)
    """
    cache = None
    graph = None
    
    if enable_cache:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "sentilyze-v5-clean")
        storage_bucket = os.getenv("CACHE_STORAGE_BUCKET", f"{project_id}-cache")
        
        cache = FirebaseSemanticCache(
            firestore_client=firestore_client or get_firestore_client(),
            storage_bucket=storage_bucket,
        )
    
    if enable_graph:
        graph = KnowledgeGraphBuilder(
            firestore_client=firestore_client or get_firestore_client(),
        )
    
    return MLServicesIntegration(semantic_cache=cache, knowledge_graph=graph)
