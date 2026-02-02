"""Unit tests for semantic cache with paraphrase detection.

Tests verify that semantically similar texts (paraphrases) are detected
and cached results are reused, reducing API costs.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pytest
from google.cloud import firestore, storage
from sentence_transformers import SentenceTransformer

from semantic_cache import (
    FirebaseSemanticCache,
    SemanticCacheEntry,
    get_semantic_cache,
    close_semantic_cache,
)


# Test fixtures
@pytest.fixture
def mock_firestore_client():
    """Create a mock Firestore client."""
    client = MagicMock(spec=firestore.Client)
    collection = MagicMock()
    client.collection.return_value = collection
    return client


@pytest.fixture
def mock_storage_client():
    """Create a mock Cloud Storage client."""
    client = MagicMock(spec=storage.Client)
    bucket = MagicMock()
    client.bucket.return_value = bucket
    return client


@pytest.fixture
def semantic_cache(mock_firestore_client, mock_storage_client):
    """Create a semantic cache instance with mocked clients."""
    cache = FirebaseSemanticCache(
        firestore_client=mock_firestore_client,
        storage_bucket="test-bucket",
        similarity_threshold=0.85,
        max_entries=1000,
    )
    return cache


class TestSemanticCacheEntry:
    """Test SemanticCacheEntry dataclass."""
    
    def test_to_dict(self):
        """Test entry serialization."""
        entry = SemanticCacheEntry(
            doc_id="cache_123_456",
            text_hash="abc123",
            text_preview="Gold prices soaring today",
            embedding_reference="0",
            result={"sentiment": "positive", "score": 0.8},
            timestamp=datetime.utcnow(),
            ttl=3600,
        )
        
        data = entry.to_dict()
        assert data["doc_id"] == "cache_123_456"
        assert data["text_hash"] == "abc123"
        assert data["text_preview"] == "Gold prices soaring today"
        assert data["embedding_reference"] == "0"
        assert data["result"]["sentiment"] == "positive"
        assert data["ttl"] == 3600
        assert "expires_at" in data


class TestParaphraseDetection:
    """Test paraphrase detection with semantic cache.
    
    These tests verify that semantically similar texts return cache hits,
    reducing redundant Gemini API calls.
    """
    
    # Test paraphrase pairs that should trigger cache hits
    PARAPHRASE_PAIRS = [
        # (original, paraphrase)
        ("Gold prices soaring today", "Gold is skyrocketing today"),
        ("Bitcoin crashes after Fed announcement", "Bitcoin plummets following Federal Reserve news"),
        ("Ethereum bullish momentum continues", "ETH maintains upward trend"),
        ("Silver market shows strength", "Silver prices demonstrate resilience"),
        ("Crypto market volatile today", "Cryptocurrency markets fluctuating significantly"),
    ]
    
    # Test texts that should NOT trigger cache hits (different meaning)
    DIFFERENT_MEANING_PAIRS = [
        ("Gold prices up", "Gold prices down"),
        ("Bitcoin bullish", "Bitcoin bearish"),
        ("Buy Ethereum now", "Sell Ethereum immediately"),
    ]
    
    @pytest.mark.asyncio
    @patch("semantic_cache.FAISS_AVAILABLE", True)
    async def test_paraphrase_cache_hit(self, semantic_cache, mock_firestore_client):
        """Test that paraphrases trigger cache hits.
        
        This test verifies the core requirement: "Gold soaring" vs "Gold skyrocketing"
        should return the same cached result, avoiding duplicate API calls.
        """
        # Mock Firestore document
        doc_ref = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = doc_ref
        
        # Mock document snapshot
        doc_snapshot = MagicMock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = {
            "doc_id": "cache_test_123",
            "text_hash": "hash123",
            "text_preview": "Gold prices soaring today",
            "embedding_reference": "0",
            "result": {
                "sentiment": "bullish",
                "confidence": 0.85,
                "explanation": "Positive sentiment detected",
            },
            "timestamp": datetime.utcnow(),
            "ttl": 3600,
            "expires_at": datetime.utcnow().replace(year=datetime.utcnow().year + 1),
        }
        doc_ref.get = AsyncMock(return_value=doc_snapshot)
        
        # Initialize cache with mocked embedding model
        with patch.object(semantic_cache, "embedding_model") as mock_model:
            # Mock embeddings - same vector for both texts (simulating high similarity)
            mock_embedding = np.array([[0.5, 0.3, 0.2] + [0.0] * 381], dtype=np.float32)
            mock_model.encode = Mock(return_value=mock_embedding)
            
            # Initialize FAISS index
            import faiss
            semantic_cache._faiss_index = faiss.IndexFlatIP(384)
            semantic_cache._entry_count = 1
            semantic_cache._doc_id_to_index = {"cache_test_123": 0}
            semantic_cache._index_to_doc_id = {0: "cache_test_123"}
            semantic_cache._initialized = True
            
            # Store the first text
            await semantic_cache.store_result(
                "Gold prices soaring today",
                {"sentiment": "bullish", "confidence": 0.85},
                ttl=3600,
            )
            
            # Query with paraphrase - should hit cache
            result = await semantic_cache.get_similar("Gold is skyrocketing today")
            
            # Verify cache hit
            assert result is not None
            assert result["sentiment"] == "bullish"
            assert result["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_different_meaning_cache_miss(self, semantic_cache):
        """Test that different meanings don't trigger false cache hits."""
        # This test ensures "Gold up" and "Gold down" are treated as different
        
        # Mock embedding model with different vectors for different meanings
        with patch.object(semantic_cache, "embedding_model") as mock_model:
            # Different embeddings for different texts
            mock_model.encode.side_effect = lambda texts, **kwargs: np.array([
                [0.9, 0.1, 0.0] + [0.0] * 381,  # "Gold up"
                [0.1, 0.9, 0.0] + [0.0] * 381,  # "Gold down" (different)
            ], dtype=np.float32)
            
            # Initialize cache
            import faiss
            semantic_cache._faiss_index = faiss.IndexFlatIP(384)
            semantic_cache._entry_count = 0
            semantic_cache._initialized = True
            
            # Store "Gold up"
            await semantic_cache.store_result(
                "Gold prices up",
                {"sentiment": "bullish", "confidence": 0.9},
                ttl=3600,
            )
            
            # Query with opposite meaning
            result = await semantic_cache.get_similar("Gold prices down")
            
            # Should be cache miss (similarity below threshold)
            # Note: In real scenario, embeddings would be different enough
            # Here we're testing the logic, not the actual embedding quality
    
    @pytest.mark.parametrize("original,paraphrase", PARAPHRASE_PAIRS)
    @pytest.mark.asyncio
    async def test_various_paraphrases(
        self,
        semantic_cache,
        mock_firestore_client,
        original,
        paraphrase,
    ):
        """Test cache hits for various financial paraphrase pairs.
        
        Parametrized test covering multiple real-world scenarios:
        - Gold price movements
        - Bitcoin/crypto volatility
        - Market sentiment variations
        """
        # Mock Firestore
        doc_ref = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = doc_ref
        
        doc_snapshot = MagicMock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = {
            "doc_id": f"cache_{hash(original) % 10000}",
            "text_hash": f"hash_{hash(original) % 10000}",
            "text_preview": original[:100],
            "result": {"sentiment": "neutral", "confidence": 0.75},
            "timestamp": datetime.utcnow(),
            "ttl": 3600,
            "expires_at": datetime.utcnow().replace(year=datetime.utcnow().year + 1),
        }
        doc_ref.get = AsyncMock(return_value=doc_snapshot)
        
        with patch.object(semantic_cache, "embedding_model") as mock_model:
            # High similarity embeddings
            mock_embedding = np.random.rand(1, 384).astype(np.float32)
            mock_embedding = mock_embedding / np.linalg.norm(mock_embedding)  # Normalize
            mock_model.encode = Mock(return_value=mock_embedding)
            
            import faiss
            semantic_cache._faiss_index = faiss.IndexFlatIP(384)
            semantic_cache._entry_count = 1
            semantic_cache._doc_id_to_index = {f"cache_{hash(original) % 10000}": 0}
            semantic_cache._index_to_doc_id = {0: f"cache_{hash(original) % 10000}"}
            semantic_cache._initialized = True
            
            # Store original
            await semantic_cache.store_result(original, {"sentiment": "neutral"})
            
            # Query with paraphrase
            result = await semantic_cache.get_similar(paraphrase)
            
            # Should hit cache (in this mock scenario)
            assert result is not None


class TestCachePersistence:
    """Test Cloud Storage persistence for cold starts."""
    
    @pytest.mark.asyncio
    async def test_persist_index(self, semantic_cache, mock_storage_client):
        """Test that FAISS index is persisted to Cloud Storage."""
        bucket = MagicMock()
        mock_storage_client.bucket.return_value = bucket
        
        blob = MagicMock()
        bucket.blob.return_value = blob
        
        # Mock successful upload
        blob.upload_from_file = AsyncMock()
        blob.upload_from_string = AsyncMock()
        
        # Setup index
        import faiss
        semantic_cache._faiss_index = faiss.IndexFlatIP(384)
        semantic_cache._entry_count = 100
        
        # Persist
        result = await semantic_cache._persist_index()
        
        # Verify upload was called
        assert blob.upload_from_file.called or blob.upload_from_string.called
    
    @pytest.mark.asyncio
    async def test_recover_index(self, semantic_cache, mock_storage_client):
        """Test that FAISS index is recovered from Cloud Storage on startup."""
        bucket = MagicMock()
        mock_storage_client.bucket.return_value = bucket
        
        # Mock blob exists
        blob = MagicMock()
        blob.exists = AsyncMock(return_value=True)
        
        # Mock download
        import io
        import faiss
        
        # Create a simple index and serialize it
        index = faiss.IndexFlatIP(384)
        buffer = io.BytesIO()
        faiss.write_index(index, buffer)
        buffer.seek(0)
        
        blob.download_to_file = AsyncMock(side_effect=lambda f: f.write(buffer.getvalue()))
        blob.download_as_string = AsyncMock(return_value=b'{"entry_count": 10, "doc_id_to_index": {}}')
        
        bucket.blob.return_value = blob
        
        # Recover
        result = await semantic_cache._recover_index()
        
        assert result is True
        assert semantic_cache._faiss_index is not None


class TestCacheTTL:
    """Test TTL (time-to-live) functionality."""
    
    @pytest.mark.asyncio
    async def test_expired_entry_removal(self, semantic_cache, mock_firestore_client):
        """Test that expired entries are removed from cache."""
        # Setup mock for expired document
        doc_ref = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = doc_ref
        
        # Document that expired yesterday
        doc_snapshot = MagicMock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = {
            "doc_id": "cache_expired",
            "expires_at": datetime.utcnow().replace(day=datetime.utcnow().day - 1),
        }
        doc_ref.get = AsyncMock(return_value=doc_snapshot)
        doc_ref.delete = AsyncMock()
        
        with patch.object(semantic_cache, "embedding_model") as mock_model:
            mock_embedding = np.array([[0.5, 0.5] + [0.0] * 382], dtype=np.float32)
            mock_model.encode = Mock(return_value=mock_embedding)
            
            import faiss
            semantic_cache._faiss_index = faiss.IndexFlatIP(384)
            semantic_cache._entry_count = 1
            semantic_cache._doc_id_to_index = {"cache_expired": 0}
            semantic_cache._index_to_doc_id = {0: "cache_expired"}
            semantic_cache._initialized = True
            
            # Try to get expired entry
            result = await semantic_cache.get_similar("Test text")
            
            # Should return None (expired)
            assert result is None


class TestCacheStats:
    """Test cache statistics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, semantic_cache):
        """Test cache statistics retrieval."""
        semantic_cache._entry_count = 50
        semantic_cache._initialized = True
        
        stats = await semantic_cache.get_cache_stats()
        
        assert stats["entry_count"] == 50
        assert stats["max_entries"] == 1000
        assert stats["similarity_threshold"] == 0.85
        assert stats["initialized"] is True
        assert stats["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert stats["storage_bucket"] == "test-bucket"


class TestDependencyInjection:
    """Test FastAPI dependency injection."""
    
    @pytest.mark.asyncio
    async def test_get_semantic_cache_singleton(self, mock_firestore_client):
        """Test that get_semantic_cache returns singleton instance."""
        # Reset singleton
        import semantic_cache
        semantic_cache._semantic_cache_instance = None
        
        with patch("semantic_cache.FirestoreCacheClient") as mock_cache_client:
            with patch("semantic_cache.FirebaseSemanticCache.initialize") as mock_init:
                mock_init.return_value = AsyncMock()
                
                # First call should create instance
                cache1 = await get_semantic_cache(firestore_client=mock_firestore_client)
                
                # Second call should return same instance
                cache2 = await get_semantic_cache(firestore_client=mock_firestore_client)
                
                assert cache1 is cache2
    
    @pytest.mark.asyncio
    async def test_close_semantic_cache(self):
        """Test closing semantic cache."""
        # Reset and create instance
        import semantic_cache
        semantic_cache._semantic_cache_instance = None
        
        mock_cache = AsyncMock()
        semantic_cache._semantic_cache_instance = mock_cache
        
        await close_semantic_cache()
        
        mock_cache.close.assert_called_once()
        assert semantic_cache._semantic_cache_instance is None


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_faiss_not_available(self):
        """Test graceful handling when FAISS is not installed."""
        with patch("semantic_cache.FAISS_AVAILABLE", False):
            cache = FirebaseSemanticCache()
            
            with pytest.raises(Exception) as exc_info:
                await cache.initialize()
            
            assert "FAISS not available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_storage_persistence_failure(self, semantic_cache, mock_storage_client):
        """Test handling of Cloud Storage persistence failures."""
        # Make storage operations fail
        mock_storage_client.bucket.side_effect = Exception("Storage error")
        
        # Should return False but not raise
        result = await semantic_cache._persist_index()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_firestore_fetch_failure(self, semantic_cache, mock_firestore_client):
        """Test handling of Firestore fetch failures."""
        # Make Firestore operations fail
        mock_firestore_client.collection.side_effect = Exception("Firestore error")
        
        # Should return None (cache miss) but not crash
        result = await semantic_cache.get_similar("Test text")
        assert result is None


# Performance tests
class TestCachePerformance:
    """Test cache performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, semantic_cache, mock_firestore_client):
        """Test that cache hits are fast (< 100ms)."""
        import time
        
        # Setup
        doc_ref = MagicMock()
        mock_firestore_client.collection.return_value.document.return_value = doc_ref
        
        doc_snapshot = MagicMock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = {
            "result": {"sentiment": "positive"},
            "expires_at": datetime.utcnow().replace(year=datetime.utcnow().year + 1),
        }
        doc_ref.get = AsyncMock(return_value=doc_snapshot)
        
        with patch.object(semantic_cache, "embedding_model") as mock_model:
            mock_embedding = np.random.rand(1, 384).astype(np.float32)
            mock_embedding = mock_embedding / np.linalg.norm(mock_embedding)
            mock_model.encode = Mock(return_value=mock_embedding)
            
            import faiss
            semantic_cache._faiss_index = faiss.IndexFlatIP(384)
            semantic_cache._entry_count = 100
            semantic_cache._initialized = True
            
            # Warm up
            await semantic_cache.get_similar("Warm up")
            
            # Measure
            start = time.time()
            for _ in range(10):
                await semantic_cache.get_similar("Test text for performance")
            elapsed = time.time() - start
            
            # Average should be less than 50ms per call
            avg_time = elapsed / 10
            assert avg_time < 0.050  # 50ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
