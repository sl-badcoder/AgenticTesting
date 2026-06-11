import time
from typing import Any

from src.database.cache.base import CacheConfig, CacheConnection


class InMemoryCacheConnection(CacheConnection):
    def __init__(self, config: CacheConfig) -> None:
        super().__init__(config)
        self._store: dict[str, tuple[Any, float | None]] = {}

    def connect(self) -> None:
        if self.is_connected:
            return

        self._connection = self._store

    def close(self) -> None:
        self._connection = None

    def get(self, key: str) -> Any | None:
        self._ensure_connected()
        namespaced_key = self.namespaced_key(key)
        cached = self._store.get(namespaced_key)
        if cached is None:
            return None

        value, expires_at = cached
        if expires_at is not None and expires_at <= time.time():
            self._store.pop(namespaced_key, None)
            return None

        return value

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._ensure_connected()
        ttl = ttl_seconds if ttl_seconds is not None else self.config.default_ttl_seconds
        expires_at = time.time() + ttl if ttl is not None else None
        self._store[self.namespaced_key(key)] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._ensure_connected()
        self._store.pop(self.namespaced_key(key), None)

    def clear(self) -> None:
        self._ensure_connected()
        prefix = f"{self.config.namespace}:"
        for key in list(self._store):
            if key.startswith(prefix):
                self._store.pop(key, None)

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            self.connect()
