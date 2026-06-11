import json
from typing import Any

from src.database.cache.base import CacheConfig, CacheConnection
from src.database.exceptions import DatabaseConnectionError


class RedisCacheConnection(CacheConnection):
    def connect(self) -> None:
        if self.is_connected:
            return

        try:
            import redis
        except ImportError as error:
            raise DatabaseConnectionError(
                "Redis cache support requires the 'redis' package."
            ) from error

        connection_options = {
            "host": self.config.host or "localhost",
            "port": self.config.port or 6379,
            "db": int(self.config.database or 0),
            "username": self.config.username,
            "password": self.config.password,
            "decode_responses": True,
            **self.config.options,
        }
        connection_options = {
            key: value for key, value in connection_options.items() if value is not None
        }

        try:
            self._connection = redis.Redis(**connection_options)
            self._connection.ping()
        except Exception as error:
            raise DatabaseConnectionError("Could not connect to Redis cache.") from error

    def close(self) -> None:
        if not self.is_connected:
            return

        self._connection.close()
        self._connection = None

    def get(self, key: str) -> Any | None:
        self._ensure_connected()
        raw_value = self._connection.get(self.namespaced_key(key))
        return json.loads(raw_value) if raw_value is not None else None

    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._ensure_connected()
        ttl = ttl_seconds if ttl_seconds is not None else self.config.default_ttl_seconds
        self._connection.set(
            name=self.namespaced_key(key),
            value=json.dumps(value, default=str),
            ex=ttl,
        )

    def delete(self, key: str) -> None:
        self._ensure_connected()
        self._connection.delete(self.namespaced_key(key))

    def clear(self) -> None:
        self._ensure_connected()
        prefix = self.namespaced_key("*")
        keys = list(self._connection.scan_iter(match=prefix))
        if keys:
            self._connection.delete(*keys)

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            self.connect()
