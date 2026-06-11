import hashlib
import json
from typing import Any

from src.database.base import DatabaseConnection, QueryParameters, QueryResult
from src.database.cache.base import CacheConnection


class CachedDatabaseConnection(DatabaseConnection):
    def __init__(
        self,
        database: DatabaseConnection,
        cache: CacheConnection,
        ttl_seconds: int | None = None,
    ) -> None:
        super().__init__(database.config)
        self.database = database
        self.cache = cache
        self.ttl_seconds = ttl_seconds

    def connect(self) -> None:
        self.database.connect()
        self.cache.connect()
        self._connection = self.database

    def close(self) -> None:
        self.database.close()
        self.cache.close()
        self._connection = None

    def execute(self, query: str, parameters: QueryParameters = None) -> int:
        self._ensure_connected()
        row_count = self.database.execute(query, parameters)
        self.cache.clear()
        return row_count

    def fetch_one(
        self,
        query: str,
        parameters: QueryParameters = None,
    ) -> dict[str, Any] | None:
        rows = self.fetch_all(query, parameters)
        return rows[0] if rows else None

    def fetch_all(
        self,
        query: str,
        parameters: QueryParameters = None,
    ) -> QueryResult:
        self._ensure_connected()
        cache_key = self._query_cache_key("fetch_all", query, parameters)
        cached_value = self.cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        rows = self.database.fetch_all(query, parameters)
        self.cache.set(cache_key, rows, self.ttl_seconds)
        return rows

    def begin_transaction(self) -> None:
        self._ensure_connected()
        self.database.begin_transaction()

    def commit(self) -> None:
        self._ensure_connected()
        self.database.commit()
        self.cache.clear()

    def rollback(self) -> None:
        self._ensure_connected()
        self.database.rollback()
        self.cache.clear()

    @property
    def is_connected(self) -> bool:
        return self.database.is_connected and self.cache.is_connected

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            self.connect()

    def _query_cache_key(
        self,
        operation: str,
        query: str,
        parameters: QueryParameters,
    ) -> str:
        payload = {
            "database": self.database.config.database,
            "operation": operation,
            "parameters": parameters,
            "query": query,
        }
        raw_key = json.dumps(payload, sort_keys=True, default=str)
        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return f"database-query:{digest}"
