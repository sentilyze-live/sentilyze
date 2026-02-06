"""Firestore cache client for GCP native caching (Redis alternative).

Uses Google Cloud Firestore instead of Redis for:
- Lower cost (free tier: 1GB + 50k ops/day)
- Native TTL support
- No VPC connector needed (unlike Memorystore)
- Serverless scaling

Cost comparison (monthly):
- Redis Memorystore: $25-40 + $15 VPC = ~$40-55
- Firestore: ~$3 (after free tier) = ~$3
- Savings: 90%+
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from google.cloud import firestore
from google.api_core.exceptions import NotFound

from .config import get_settings
from .logging import get_logger
from .exceptions import CacheError

logger = get_logger(__name__)
settings = get_settings()


class FirestoreCacheClient:
    """Firestore-based cache client (Redis alternative for GCP)."""
    
    def __init__(self, project_id: Optional[str] = None) -> None:
        self.project_id = project_id or settings.google_cloud_project
        self._client: Optional[firestore.Client] = None
        self._collection = "sentilyze_cache"
    
    @property
    def client(self) -> firestore.Client:
        """Get or create Firestore client."""
        if self._client is None:
            self._client = firestore.Client(project=self.project_id)
        return self._client
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache."""
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")
            doc = await asyncio.to_thread(doc_ref.get)
            
            if not doc.exists:
                return None
            
            data = doc.to_dict()
            
            # Check TTL
            expires_at = data.get("expires_at")
            if expires_at and expires_at < datetime.now(timezone.utc):
                await asyncio.to_thread(doc_ref.delete)
                return None
            
            return data.get("value")
            
        except NotFound:
            return None
        except Exception as e:
            logger.error("Firestore cache get failed", error=str(e), key=key)
            raise CacheError(f"Failed to get cache value: {e}", details={"key": key, "namespace": namespace}) from e
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = 3600,
        namespace: str = "default"
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")
            
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            
            data = {
                "value": value,
                "created_at": datetime.now(timezone.utc),
                "expires_at": expires_at,
                "ttl_seconds": ttl,
            }
            
            await asyncio.to_thread(doc_ref.set, data)
            return True
            
        except Exception as e:
            logger.error("Firestore cache set failed", error=str(e), key=key)
            raise CacheError(f"Failed to set cache value: {e}", details={"key": key, "namespace": namespace}) from e
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete key from cache."""
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")
            await asyncio.to_thread(doc_ref.delete)
            return True
            
        except Exception as e:
            logger.error("Firestore cache delete failed", error=str(e), key=key)
            raise CacheError(f"Failed to delete cache value: {e}", details={"key": key, "namespace": namespace}) from e
    
    async def increment(
        self, 
        key: str, 
        amount: int = 1,
        namespace: str = "default"
    ) -> int:
        """Increment counter atomically."""
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")
            
            await asyncio.to_thread(
                doc_ref.update,
                {"value": firestore.Increment(amount)}
            )
            
            doc = await asyncio.to_thread(doc_ref.get)
            if doc.exists:
                return doc.to_dict().get("value", 0)
            return 0
            
        except Exception as e:
            logger.error("Firestore cache increment failed", error=str(e), key=key)
            raise CacheError(f"Failed to increment cache value: {e}", details={"key": key, "namespace": namespace}) from e
    
    async def increment_with_ttl(
        self,
        key: str,
        amount: int = 1,
        ttl_seconds: int = 3600,
        namespace: str = "default",
    ) -> int:
        """Increment with TTL (creates if not exists)."""
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")
            
            doc = await asyncio.to_thread(doc_ref.get)
            
            if not doc.exists:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
                await asyncio.to_thread(
                    doc_ref.set,
                    {
                        "value": amount,
                        "created_at": datetime.now(timezone.utc),
                        "expires_at": expires_at,
                    }
                )
                return amount
            else:
                await asyncio.to_thread(
                    doc_ref.update,
                    {"value": firestore.Increment(amount)}
                )
                
                doc = await asyncio.to_thread(doc_ref.get)
                return doc.to_dict().get("value", 0)
                
        except Exception as e:
            logger.error("Firestore increment with TTL failed", error=str(e), key=key)
            raise CacheError(f"Failed to increment cache with TTL: {e}", details={"key": key, "namespace": namespace}) from e
    
    async def ttl(self, key: str, namespace: str = "default") -> int:
        """Get remaining TTL in seconds."""
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")
            doc = await asyncio.to_thread(doc_ref.get)

            if not doc.exists:
                return 0

            data = doc.to_dict()
            expires_at = data.get("expires_at")

            if not expires_at:
                return 0

            remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
            return max(0, int(remaining))

        except Exception as e:
            logger.error("Firestore TTL check failed", error=str(e), key=key)
            raise CacheError(f"Failed to check TTL: {e}", details={"key": key, "namespace": namespace}) from e

    async def add(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        namespace: str = "default"
    ) -> bool:
        """Atomic set-if-not-exists operation (for deduplication/locking).

        Returns True if key was set (didn't exist), False if key already exists.
        Uses Firestore transaction for atomicity.
        """
        try:
            doc_ref = self.client.collection(self._collection).document(f"{namespace}:{key}")

            @firestore.transactional
            def _add_transaction(transaction, ref):
                snapshot = ref.get(transaction=transaction)

                # Check if exists and not expired
                if snapshot.exists:
                    data = snapshot.to_dict()
                    expires_at = data.get("expires_at")

                    # If not expired, return False (key exists)
                    if not expires_at or expires_at > datetime.now(timezone.utc):
                        return False

                # Key doesn't exist or expired - set it
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
                transaction.set(ref, {
                    "value": value,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": expires_at,
                    "ttl_seconds": ttl,
                })
                return True

            # Run transaction
            transaction = self.client.transaction()
            result = await asyncio.to_thread(_add_transaction, transaction, doc_ref)
            return result

        except Exception as e:
            logger.error("Firestore cache add failed", error=str(e), key=key)
            raise CacheError(f"Failed to add cache value: {e}", details={"key": key, "namespace": namespace}) from e

    async def close(self) -> None:
        """Close Firestore client (no-op for Firestore)."""
        pass


def get_cache_client():
    """Get appropriate cache client based on configuration."""
    cache_type = settings.cache_type.lower() if hasattr(settings, 'cache_type') else 'redis'
    
    if cache_type == 'firestore':
        return FirestoreCacheClient()
    else:
        from .cache import CacheClient
        return CacheClient()
