"""
Three-tier caching system for HALO framework.

This module implements a hierarchical caching strategy:
- Level 1: Exact match cache (Redis)
- Level 2: Semantic cache (FAISS + Redis)
- Level 3: Summary cache (Redis)
"""

import logging
import hashlib
import pickle
import time
from typing import Optional, Any, Dict, List, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from .models import CacheEntry, CacheConfig

logger = logging.getLogger(__name__)


class ThreeTierCache:
    """Three-tier caching system for optimizing Gemini API usage."""
    
    def __init__(self, config: CacheConfig):
        """
        Initialize the three-tier cache system.
        
        Args:
            config: Cache configuration
        """
        self.config = config
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize Redis connection
        if config.use_fakeredis:
            import fakeredis
            self.redis_client = fakeredis.FakeRedis()
            logger.info("Using fakeredis for testing")
        else:
            import redis
            self.redis_client = redis.Redis(
                host=config.redis_host,
                port=config.redis_port,
                db=config.redis_db,
                decode_responses=False
            )
            logger.info(f"Connected to Redis at {config.redis_host}:{config.redis_port}")
        
        # Initialize FAISS index for semantic search
        self.faiss_index = None
        self.embedding_keys = []
        self._initialize_faiss()
        
        # Cache statistics
        self.stats = {
            'l1_hits': 0,
            'l2_hits': 0,
            'l3_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
    
    def _initialize_faiss(self):
        """Initialize FAISS index for semantic search."""
        try:
            # Create FAISS index for 384-dimensional embeddings
            dimension = 384  # all-MiniLM-L6-v2 embedding dimension
            self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            logger.info("FAISS index initialized for semantic search")
        except Exception as e:
            logger.error(f"Error initializing FAISS index: {e}")
            self.faiss_index = None
    
    def _generate_key(self, content: str) -> str:
        """Generate cache key from content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage."""
        return pickle.dumps(value)
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        return pickle.loads(data)
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text."""
        try:
            embedding = self.embedding_model.encode([text])[0]
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return np.zeros(384, dtype=np.float32)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache using three-tier strategy.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        self.stats['total_requests'] += 1
        
        # Level 1: Exact match cache
        l1_result = self._get_l1(key)
        if l1_result is not None:
            self.stats['l1_hits'] += 1
            logger.debug(f"L1 cache hit for key: {key}")
            return l1_result
        
        # Level 2: Semantic cache
        l2_result = self._get_l2(key)
        if l2_result is not None:
            self.stats['l2_hits'] += 1
            logger.debug(f"L2 cache hit for key: {key}")
            return l2_result
        
        # Level 3: Summary cache
        l3_result = self._get_l3(key)
        if l3_result is not None:
            self.stats['l3_hits'] += 1
            logger.debug(f"L3 cache hit for key: {key}")
            return l3_result
        
        self.stats['misses'] += 1
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def _get_l1(self, key: str) -> Optional[Any]:
        """Get from Level 1 (exact match) cache."""
        try:
            data = self.redis_client.get(f"l1:{key}")
            if data:
                entry = self._deserialize_value(data)
                # Update access count
                entry.access_count += 1
                self.redis_client.setex(
                    f"l1:{key}",
                    self.config.l1_ttl,
                    self._serialize_value(entry)
                )
                return entry.value
            return None
        except Exception as e:
            logger.error(f"Error accessing L1 cache: {e}")
            return None
    
    def _get_l2(self, key: str) -> Optional[Any]:
        """Get from Level 2 (semantic) cache."""
        if self.faiss_index is None:
            return None
        
        try:
            # Get embedding for the query
            query_embedding = self._get_embedding(key)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Search FAISS index
            if self.faiss_index.ntotal > 0:
                similarities, indices = self.faiss_index.search(query_embedding, 1)
                
                if similarities[0][0] >= self.config.l2_similarity_threshold:
                    # Get the most similar key
                    similar_key = self.embedding_keys[indices[0][0]]
                    
                    # Get value from Redis
                    data = self.redis_client.get(f"l2:{similar_key}")
                    if data:
                        entry = self._deserialize_value(data)
                        entry.access_count += 1
                        self.redis_client.setex(
                            f"l2:{similar_key}",
                            self.config.l2_ttl,
                            self._serialize_value(entry)
                        )
                        return entry.value
            
            return None
        except Exception as e:
            logger.error(f"Error accessing L2 cache: {e}")
            return None
    
    def _get_l3(self, key: str) -> Optional[Any]:
        """Get from Level 3 (summary) cache."""
        try:
            # Try to find a summary that matches the key pattern
            pattern = f"l3:*{key[:8]}*"  # Use first 8 characters for pattern matching
            keys = self.redis_client.keys(pattern)
            
            if keys:
                # Get the first matching key
                data = self.redis_client.get(keys[0])
                if data:
                    entry = self._deserialize_value(data)
                    entry.access_count += 1
                    self.redis_client.setex(
                        keys[0],
                        self.config.l3_ttl,
                        self._serialize_value(entry)
                    )
                    return entry.value
            
            return None
        except Exception as e:
            logger.error(f"Error accessing L3 cache: {e}")
            return None
    
    def put(self, key: str, value: Any, level: int = 1, metadata: Optional[Dict] = None):
        """
        Store value in cache at specified level.
        
        Args:
            key: Cache key
            value: Value to cache
            level: Cache level (1, 2, or 3)
            metadata: Additional metadata
        """
        try:
            entry = CacheEntry(
                key=key,
                value=value,
                size_bytes=len(self._serialize_value(value)),
                cache_level=level
            )
            
            if metadata:
                entry.timestamp = metadata.get('timestamp', entry.timestamp)
                entry.access_count = metadata.get('access_count', 0)
            
            serialized_entry = self._serialize_value(entry)
            
            if level == 1:
                self._put_l1(key, entry, serialized_entry)
            elif level == 2:
                self._put_l2(key, entry, serialized_entry)
            elif level == 3:
                self._put_l3(key, entry, serialized_entry)
            else:
                raise ValueError(f"Invalid cache level: {level}")
                
            logger.debug(f"Stored value in L{level} cache for key: {key}")
            
        except Exception as e:
            logger.error(f"Error storing value in L{level} cache: {e}")
    
    def _put_l1(self, key: str, entry: CacheEntry, serialized_entry: bytes):
        """Store in Level 1 cache."""
        # Check cache size limit
        if self._get_l1_size() >= self.config.l1_max_size:
            self._evict_l1()
        
        self.redis_client.setex(
            f"l1:{key}",
            self.config.l1_ttl,
            serialized_entry
        )
    
    def _put_l2(self, key: str, entry: CacheEntry, serialized_entry: bytes):
        """Store in Level 2 cache."""
        # Check cache size limit
        if self._get_l2_size() >= self.config.l2_max_size:
            self._evict_l2()
        
        # Store in Redis
        self.redis_client.setex(
            f"l2:{key}",
            self.config.l2_ttl,
            serialized_entry
        )
        
        # Add to FAISS index
        if self.faiss_index is not None:
            embedding = self._get_embedding(key)
            embedding = embedding.reshape(1, -1)
            self.faiss_index.add(embedding)
            self.embedding_keys.append(key)
    
    def _put_l3(self, key: str, entry: CacheEntry, serialized_entry: bytes):
        """Store in Level 3 cache."""
        # Check cache size limit
        if self._get_l3_size() >= self.config.l3_max_size:
            self._evict_l3()
        
        self.redis_client.setex(
            f"l3:{key}",
            self.config.l3_ttl,
            serialized_entry
        )
    
    def _get_l1_size(self) -> int:
        """Get number of entries in L1 cache."""
        try:
            keys = self.redis_client.keys("l1:*")
            return len(keys)
        except Exception:
            return 0
    
    def _get_l2_size(self) -> int:
        """Get number of entries in L2 cache."""
        try:
            keys = self.redis_client.keys("l2:*")
            return len(keys)
        except Exception:
            return 0
    
    def _get_l3_size(self) -> int:
        """Get number of entries in L3 cache."""
        try:
            keys = self.redis_client.keys("l3:*")
            return len(keys)
        except Exception:
            return 0
    
    def _evict_l1(self):
        """Evict least recently used entry from L1 cache."""
        try:
            keys = self.redis_client.keys("l1:*")
            if keys:
                # Simple LRU: remove the first key
                self.redis_client.delete(keys[0])
                logger.debug(f"Evicted key from L1 cache: {keys[0]}")
        except Exception as e:
            logger.error(f"Error evicting from L1 cache: {e}")
    
    def _evict_l2(self):
        """Evict least recently used entry from L2 cache."""
        try:
            keys = self.redis_client.keys("l2:*")
            if keys:
                # Simple LRU: remove the first key
                key_to_remove = keys[0].decode() if isinstance(keys[0], bytes) else keys[0]
                key_name = key_to_remove.replace("l2:", "")
                
                # Remove from Redis
                self.redis_client.delete(key_to_remove)
                
                # Remove from FAISS index (simplified - in practice, you'd need to rebuild)
                if key_name in self.embedding_keys:
                    self.embedding_keys.remove(key_name)
                
                logger.debug(f"Evicted key from L2 cache: {key_to_remove}")
        except Exception as e:
            logger.error(f"Error evicting from L2 cache: {e}")
    
    def _evict_l3(self):
        """Evict least recently used entry from L3 cache."""
        try:
            keys = self.redis_client.keys("l3:*")
            if keys:
                # Simple LRU: remove the first key
                self.redis_client.delete(keys[0])
                logger.debug(f"Evicted key from L3 cache: {keys[0]}")
        except Exception as e:
            logger.error(f"Error evicting from L3 cache: {e}")
    
    def clear(self, level: Optional[int] = None):
        """
        Clear cache entries.
        
        Args:
            level: Cache level to clear (None for all levels)
        """
        try:
            if level is None or level == 1:
                keys = self.redis_client.keys("l1:*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info("Cleared L1 cache")
            
            if level is None or level == 2:
                keys = self.redis_client.keys("l2:*")
                if keys:
                    self.redis_client.delete(*keys)
                # Reset FAISS index
                if self.faiss_index is not None:
                    self.faiss_index.reset()
                self.embedding_keys.clear()
                logger.info("Cleared L2 cache")
            
            if level is None or level == 3:
                keys = self.redis_client.keys("l3:*")
                if keys:
                    self.redis_client.delete(*keys)
                logger.info("Cleared L3 cache")
                
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['total_requests']
        if total_requests == 0:
            hit_rate = 0.0
        else:
            total_hits = self.stats['l1_hits'] + self.stats['l2_hits'] + self.stats['l3_hits']
            hit_rate = total_hits / total_requests
        
        return {
            **self.stats,
            'hit_rate': hit_rate,
            'l1_size': self._get_l1_size(),
            'l2_size': self._get_l2_size(),
            'l3_size': self._get_l3_size(),
            'total_size': self._get_l1_size() + self._get_l2_size() + self._get_l3_size()
        }
    
    def print_stats(self):
        """Print cache statistics."""
        stats = self.get_stats()
        logger.info("Cache Statistics:")
        logger.info(f"  Total Requests: {stats['total_requests']}")
        logger.info(f"  L1 Hits: {stats['l1_hits']}")
        logger.info(f"  L2 Hits: {stats['l2_hits']}")
        logger.info(f"  L3 Hits: {stats['l3_hits']}")
        logger.info(f"  Misses: {stats['misses']}")
        logger.info(f"  Hit Rate: {stats['hit_rate']:.2%}")
        logger.info(f"  L1 Size: {stats['l1_size']}")
        logger.info(f"  L2 Size: {stats['l2_size']}")
        logger.info(f"  L3 Size: {stats['l3_size']}")
        logger.info(f"  Total Size: {stats['total_size']}") 