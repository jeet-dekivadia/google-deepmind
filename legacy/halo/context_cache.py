"""
Context caching for Gemini batch prediction.
Supports in-memory and persistent (SQLite) caching.
"""
import asyncio
import aiosqlite
from typing import Any, Dict, Optional, AsyncGenerator

class InMemoryCache:
    """
    Simple in-memory cache for storing context and answers.
    Thread-safe for single-process use.
    """
    def __init__(self) -> None:
        self._cache: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache by key."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the cache."""
        self._cache[key] = value

    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return key in self._cache

    def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache.clear()

class PersistentCache:
    """
    Persistent cache using SQLite for storing context and answers.
    Safe for async use. Use as an async context manager for best results.
    """
    def __init__(self, db_path: str = "context_cache.db") -> None:
        self.db_path = db_path
        self._initialized = False

    async def _init_db(self) -> None:
        if self._initialized:
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            await db.commit()
        self._initialized = True

    async def get(self, key: str) -> Optional[str]:
        """Get a value from the persistent cache by key."""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT value FROM cache WHERE key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set(self, key: str, value: str) -> None:
        """Set a value in the persistent cache."""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "REPLACE INTO cache (key, value) VALUES (?, ?)", (key, value)
            )
            await db.commit()

    async def exists(self, key: str) -> bool:
        """Check if a key exists in the persistent cache."""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM cache WHERE key = ?", (key,)) as cursor:
                return await cursor.fetchone() is not None

    async def delete(self, key: str) -> None:
        """Delete a key from the persistent cache."""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache WHERE key = ?", (key,))
            await db.commit()

    async def clear(self) -> None:
        """Clear the entire persistent cache."""
        await self._init_db()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache")
            await db.commit()

    async def __aenter__(self):
        await self._init_db()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass 