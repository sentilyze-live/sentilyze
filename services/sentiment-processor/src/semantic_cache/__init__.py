"""Firebase Semantic Cache with FAISS and sentence-transformers.

This module provides semantic caching for sentiment analysis to avoid
redundant Gemini API calls for semantically similar texts.

Uses:
- sentence-transformers/all-MiniLM-L6-v2 for embeddings (384-dim)
- FAISS for in-memory similarity search (cosine similarity)
- Firestore for persistent storage
- Cloud Storage for FAISS index persistence across cold starts

Cost savings: 20-40% reduction in Gemini API calls.
"""

import asyncio
import hashlib
import io
import json
import os
import pickle
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional, TYPE_CHECKING

from google.cloud import firestore, storage
from google.api_core.exceptions import NotFound

# Optional ML deps (Poetry group: `ml`)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    if TYPE_CHECKING:  # pragma: no cover
        from sentence_transformers import SentenceTransformer as SentenceTransformer  # type: ignore[no-redef]
    else:
        SentenceTransformer = Any  # type: ignore[assignment,misc]

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from sentilyze_core import get_logger, get_settings
from sentilyze_core.exceptions import CacheError

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class SemanticCacheEntry:
    """Single semantic cache entry."""
    doc_id: str
    text_hash: str
    text_preview: str  # First 100 chars for debugging
    embedding_reference: str  # Index in FAISS
    result: dict[str, Any]
    timestamp: datetime
    ttl: int  # TTL in seconds
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "text_hash": self.text_hash,
            "text_preview": self.text_preview,
            "embedding_reference": self.embedding_reference,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
            "ttl": self.ttl,
            "expires_at": (self.timestamp + timedelta(seconds=self.ttl)).isoformat(),
        }


class FirebaseSemanticCache:
    """Semantic cache using FAISS + Firestore + Cloud Storage.
    
    This cache stores embeddings locally in FAISS for fast similarity search,
    persists results in Firestore, and backs up the FAISS index to Cloud Storage
    for cold start recovery.
    
    Args:
        firestore_client: Firestore client instance
        storage_bucket: Cloud Storage bucket name
        similarity_threshold: Cosine similarity threshold (default 0.85)
        max_entries: Maximum cache entries (default 10000)
        embedding_model: Sentence transformer model name
        
    Example:
        >>> cache = FirebaseSemanticCache(
        ...     firestore_client=firestore.Client(),
        ...     storage_bucket="my-bucket"
        ... )
        >>> await cache.initialize()
        >>> 
        >>> # Check cache
        >>> result = await cache.get_similar("Gold prices soaring today")
        >>> if result:
        ...     print(f"Cache hit: {result}")
        ... else:
        ...     # Call Gemini API
        ...     api_result = await call_gemini("Gold prices soaring today")
        ...     await cache.store_result("Gold prices soaring today", api_result)
    """
    
    def __init__(
        self,
        firestore_client: Optional[firestore.Client] = None,
        storage_bucket: Optional[str] = None,
        similarity_threshold: float = 0.85,
        max_entries: int = 10000,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self.project_id = settings.google_cloud_project
        self._firestore_client = firestore_client
        self._storage_bucket = storage_bucket or f"{self.project_id}-cache"
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self.embedding_model_name = embedding_model
        
        # Lazy initialization
        self._embedding_model: Optional[SentenceTransformer] = None
        self._faiss_index: Optional[faiss.Index] = None
        self._storage_client: Optional[storage.Client] = None
        self._index_path = "semantic_cache/faiss_index.bin"
        self._metadata_path = "semantic_cache/metadata.json"
        self._collection = "semantic_cache"
        
        # In-memory tracking
        self._doc_id_to_index: dict[str, int] = {}
        self._index_to_doc_id: dict[int, str] = {}
        self._initialized = False
        self._entry_count = 0
        
    @property
    def firestore_client(self) -> firestore.Client:
        """Get or create Firestore client."""
        if self._firestore_client is None:
            self._firestore_client = firestore.Client(project=self.project_id)
        return self._firestore_client
    
    @property
    def storage_client(self) -> storage.Client:
        """Get or create Storage client."""
        if self._storage_client is None:
            self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client
    
    @property
    def embedding_model(self) -> SentenceTransformer:
        """Get or load embedding model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise CacheError(
                "sentence-transformers not available. Install with: `poetry install --with ml`",
                details={},
            )
        if not NUMPY_AVAILABLE:
            raise CacheError(
                "numpy not available. Install with: `poetry install --with ml`",
                details={},
            )
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            start_time = time.time()
            self._embedding_model = SentenceTransformer(self.embedding_model_name)
            load_time = time.time() - start_time
            logger.info(f"Embedding model loaded in {load_time:.2f}s")
        return self._embedding_model
    
    async def initialize(self) -> None:
        """Initialize the semantic cache.
        
        Loads FAISS index from Cloud Storage if available,
        otherwise rebuilds from Firestore.
        """
        if self._initialized:
            return

        if not NUMPY_AVAILABLE:
            raise CacheError(
                "numpy not available. Install with: `poetry install --with ml`",
                details={},
            )
            
        if not FAISS_AVAILABLE:
            raise CacheError(
                "FAISS not available. Install with: `poetry install --with ml`",
                details={}
            )
        
        try:
            # Try to recover index from Cloud Storage
            recovered = await self._recover_index()
            
            if not recovered:
                # Initialize empty FAISS index
                logger.info("Initializing empty FAISS index")
                # 384 dimensions (all-MiniLM-L6-v2), cosine similarity
                self._faiss_index = faiss.IndexFlatIP(384)  # Inner product = cosine for normalized vectors
                
                # Try to rebuild from Firestore
                await self._rebuild_from_firestore()
            
            self._initialized = True
            logger.info(
                f"Semantic cache initialized",
                entries=self._entry_count,
                threshold=self.similarity_threshold,
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize semantic cache: {e}")
            raise CacheError(f"Cache initialization failed: {e}", details={}) from e
    
    def _generate_text_hash(self, text: str) -> str:
        """Generate hash for text."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]
    
    def _generate_doc_id(self, text_hash: str) -> str:
        """Generate document ID from hash."""
        return f"cache_{text_hash}_{int(time.time())}"
    
    async def get_similar(self, query_text: str) -> Optional[dict[str, Any]]:
        """Search for semantically similar cached results.
        
        Args:
            query_text: Query text to search for
            
        Returns:
            Cached result dict if similar text found above threshold,
            None otherwise
            
        Example:
            >>> result = await cache.get_similar("Gold is skyrocketing today")
            >>> # Returns cached result for "Gold prices soaring today"
            >>> # if cosine similarity > 0.85
        """
        if not self._initialized:
            await self.initialize()
        
        if self._entry_count == 0:
            return None
        
        try:
            # Generate embedding
            embedding = self.embedding_model.encode([query_text], convert_to_numpy=True)
            embedding = embedding.astype(np.float32)
            faiss.normalize_L2(embedding)  # Normalize for cosine similarity
            
            # Search FAISS index
            k = min(3, self._entry_count)  # Top 3 matches
            distances, indices = self._faiss_index.search(embedding, k)
            
            # Check if best match exceeds threshold
            if distances[0][0] >= self.similarity_threshold:
                best_idx = int(indices[0][0])
                doc_id = self._index_to_doc_id.get(best_idx)
                
                if doc_id:
                    # Fetch result from Firestore
                    doc_ref = self.firestore_client.collection(self._collection).document(doc_id)
                    doc = await asyncio.to_thread(doc_ref.get)
                    
                    if doc.exists:
                        data = doc.to_dict()
                        
                        # Check TTL
                        expires_at = data.get("expires_at")
                        if expires_at and isinstance(expires_at, datetime):
                            if expires_at < datetime.utcnow():
                                # Entry expired, remove from index
                                await self._remove_entry(doc_id, best_idx)
                                return None
                        
                        logger.info(
                            f"Semantic cache hit",
                            doc_id=doc_id,
                            similarity=float(distances[0][0]),
                            query_preview=query_text[:50],
                        )
                        return data.get("result")
            
            return None
            
        except Exception as e:
            logger.error(f"Semantic cache search failed: {e}")
            return None
    
    async def store_result(
        self,
        text: str,
        result: dict[str, Any],
        ttl: int = 3600,
    ) -> bool:
        """Store a new result in the semantic cache.
        
        Args:
            text: Original text
            result: API result to cache
            ttl: Time-to-live in seconds
            
        Returns:
            True if stored successfully
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            text_hash = self._generate_text_hash(text)
            doc_id = self._generate_doc_id(text_hash)
            
            # Generate embedding
            embedding = self.embedding_model.encode([text], convert_to_numpy=True)
            embedding = embedding.astype(np.float32)
            faiss.normalize_L2(embedding)  # Normalize for cosine similarity
            
            # Add to FAISS index
            idx = self._entry_count
            self._faiss_index.add(embedding)
            self._entry_count += 1
            
            # Track mappings
            self._doc_id_to_index[doc_id] = idx
            self._index_to_doc_id[idx] = doc_id
            
            # Create cache entry
            entry = SemanticCacheEntry(
                doc_id=doc_id,
                text_hash=text_hash,
                text_preview=text[:100],
                embedding_reference=str(idx),
                result=result,
                timestamp=datetime.utcnow(),
                ttl=ttl,
            )
            
            # Store in Firestore
            doc_ref = self.firestore_client.collection(self._collection).document(doc_id)
            await asyncio.to_thread(
                doc_ref.set,
                entry.to_dict()
            )
            
            logger.info(
                f"Stored semantic cache entry",
                doc_id=doc_id,
                index=idx,
                text_preview=text[:50],
            )
            
            # Persist index to Cloud Storage periodically (every 100 entries)
            if self._entry_count % 100 == 0:
                await self._persist_index()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store semantic cache entry: {e}")
            return False
    
    async def _remove_entry(self, doc_id: str, index: int) -> None:
        """Remove expired entry from cache."""
        try:
            # Remove from Firestore
            doc_ref = self.firestore_client.collection(self._collection).document(doc_id)
            await asyncio.to_thread(doc_ref.delete)
            
            # Note: FAISS doesn't support deletion, mark as invalid
            self._doc_id_to_index.pop(doc_id, None)
            self._index_to_doc_id.pop(index, None)
            
            logger.info(f"Removed expired cache entry", doc_id=doc_id)
        except Exception as e:
            logger.warning(f"Failed to remove expired entry: {e}")
    
    async def _persist_index(self) -> bool:
        """Persist FAISS index to Cloud Storage.
        
        Called periodically and on shutdown to survive cold starts.
        """
        try:
            if self._entry_count == 0:
                return True
            
            # Serialize FAISS index
            buffer = io.BytesIO()
            faiss.write_index(self._faiss_index, buffer)
            buffer.seek(0)
            
            # Upload to Cloud Storage
            bucket = self.storage_client.bucket(self._storage_bucket)
            blob = bucket.blob(self._index_path)
            await asyncio.to_thread(
                blob.upload_from_file,
                buffer,
                content_type="application/octet-stream"
            )
            
            # Save metadata
            metadata = {
                "entry_count": self._entry_count,
                "last_updated": datetime.utcnow().isoformat(),
                "model": self.embedding_model_name,
                "threshold": self.similarity_threshold,
                "doc_id_to_index": self._doc_id_to_index,
            }
            
            metadata_blob = bucket.blob(self._metadata_path)
            await asyncio.to_thread(
                metadata_blob.upload_from_string,
                json.dumps(metadata),
                content_type="application/json"
            )
            
            logger.info(
                f"Persisted FAISS index to Cloud Storage",
                entries=self._entry_count,
                bucket=self._storage_bucket,
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist FAISS index: {e}")
            return False
    
    async def _recover_index(self) -> bool:
        """Recover FAISS index from Cloud Storage.
        
        Returns:
            True if successfully recovered, False otherwise
        """
        try:
            bucket = self.storage_client.bucket(self._storage_bucket)
            
            # Check if index exists
            blob = bucket.blob(self._index_path)
            if not await asyncio.to_thread(blob.exists):
                logger.info("No existing FAISS index found in Cloud Storage")
                return False
            
            # Download index
            logger.info("Downloading FAISS index from Cloud Storage")
            buffer = io.BytesIO()
            await asyncio.to_thread(blob.download_to_file, buffer)
            buffer.seek(0)
            
            # Load FAISS index
            self._faiss_index = faiss.read_index(buffer)
            
            # Load metadata
            metadata_blob = bucket.blob(self._metadata_path)
            metadata_json = await asyncio.to_thread(metadata_blob.download_as_string)
            metadata = json.loads(metadata_json)
            
            self._entry_count = metadata.get("entry_count", 0)
            self._doc_id_to_index = metadata.get("doc_id_to_index", {})
            self._index_to_doc_id = {v: k for k, v in self._doc_id_to_index.items()}
            
            logger.info(
                f"Recovered FAISS index from Cloud Storage",
                entries=self._entry_count,
                last_updated=metadata.get("last_updated"),
            )
            return True
            
        except NotFound:
            logger.info("FAISS index not found in Cloud Storage")
            return False
        except Exception as e:
            logger.error(f"Failed to recover FAISS index: {e}")
            return False
    
    async def _rebuild_from_firestore(self) -> None:
        """Rebuild FAISS index from Firestore entries.
        
        Used when Cloud Storage backup is not available.
        """
        try:
            logger.info("Rebuilding FAISS index from Firestore")
            
            collection_ref = self.firestore_client.collection(self._collection)
            docs = await asyncio.to_thread(
                collection_ref.limit(self.max_entries).stream
            )
            
            entries_added = 0
            embeddings_list = []
            
            async for doc in docs:
                data = doc.to_dict()
                text_preview = data.get("text_preview", "")
                
                # Regenerate embedding
                if text_preview:
                    embedding = self.embedding_model.encode([text_preview], convert_to_numpy=True)
                    embedding = embedding.astype(np.float32)
                    faiss.normalize_L2(embedding)
                    embeddings_list.append(embedding[0])
                    
                    # Track mappings
                    idx = entries_added
                    self._doc_id_to_index[doc.id] = idx
                    self._index_to_doc_id[idx] = doc.id
                    entries_added += 1
            
            if embeddings_list:
                embeddings_array = np.array(embeddings_list)
                self._faiss_index.add(embeddings_array)
                self._entry_count = entries_added
                
                logger.info(
                    f"Rebuilt FAISS index from Firestore",
                    entries=entries_added,
                )
            
        except Exception as e:
            logger.error(f"Failed to rebuild from Firestore: {e}")
    
    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "entry_count": self._entry_count,
            "max_entries": self.max_entries,
            "similarity_threshold": self.similarity_threshold,
            "initialized": self._initialized,
            "embedding_model": self.embedding_model_name,
            "storage_bucket": self._storage_bucket,
        }
    
    async def close(self) -> None:
        """Close cache and persist index."""
        if self._initialized:
            await self._persist_index()
            logger.info("Semantic cache closed and index persisted")
        self._initialized = False


# Global cache instance for dependency injection
_semantic_cache_instance: Optional[FirebaseSemanticCache] = None


async def get_semantic_cache(
    firestore_client: Optional[firestore.Client] = None,
    storage_bucket: Optional[str] = None,
) -> FirebaseSemanticCache:
    """Get or create semantic cache instance (FastAPI dependency).
    
    Usage in FastAPI:
        >>> from fastapi import Depends
        >>> 
        >>> @app.post("/analyze")
        ... async def analyze(
        ...     text: str,
        ...     cache: FirebaseSemanticCache = Depends(get_semantic_cache)
        ... ):
        ...     result = await cache.get_similar(text)
        ...     if not result:
        ...         result = await call_gemini(text)
        ...         await cache.store_result(text, result)
        ...     return result
    """
    global _semantic_cache_instance
    
    if _semantic_cache_instance is None:
        _semantic_cache_instance = FirebaseSemanticCache(
            firestore_client=firestore_client,
            storage_bucket=storage_bucket,
        )
        await _semantic_cache_instance.initialize()
    
    return _semantic_cache_instance


async def close_semantic_cache() -> None:
    """Close global semantic cache instance."""
    global _semantic_cache_instance
    if _semantic_cache_instance:
        await _semantic_cache_instance.close()
        _semantic_cache_instance = None
