import time
from typing import Any


class ResponseCache:
    """In-memory key-value cache with TTL expiration for API and feed responses."""

    def __init__(self, default_ttl_seconds: int = 3600) -> None:
        self.default_ttl = default_ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        """Retrieve cached value if present and not expired."""
        if key not in self._store:
            return None
        expires_at, value = self._store[key]
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store value with specified TTL."""
        ttl = self.default_ttl if ttl_seconds is None else ttl_seconds
        self._store[key] = (time.time() + ttl, value)

    def delete(self, key: str) -> None:
        """Evict key if present."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._store.clear()


response_cache = ResponseCache()
