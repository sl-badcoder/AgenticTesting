from typing import Any

from src.database.base import DatabaseConfig, DatabaseConnection, QueryParameters, QueryResult
from src.database.cache import CacheConfig
from src.database.cache.cached_database import CachedDatabaseConnection
from src.database.cache.vendor.in_memory import InMemoryCacheConnection


class FakeDatabaseConnection(DatabaseConnection):
    def __init__(self) -> None:
        super().__init__(DatabaseConfig(vendor="fake", database="test"))
        self.fetch_all_calls = 0
        self.execute_calls = 0
        self.commits = 0
        self.rollbacks = 0
        self.transaction_open = False

    def connect(self) -> None:
        self._connection = object()

    def close(self) -> None:
        self._connection = None

    def execute(self, query: str, parameters: QueryParameters = None) -> int:
        self.execute_calls += 1
        return 1

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
        self.fetch_all_calls += 1
        return [{"call": self.fetch_all_calls, "query": query}]

    def begin_transaction(self) -> None:
        self.transaction_open = True

    def commit(self) -> None:
        self.commits += 1
        self.transaction_open = False

    def rollback(self) -> None:
        self.rollbacks += 1
        self.transaction_open = False


def create_cached_database() -> tuple[CachedDatabaseConnection, FakeDatabaseConnection]:
    database = FakeDatabaseConnection()
    cache = InMemoryCacheConnection(CacheConfig(vendor="memory", namespace="cached-db"))
    return CachedDatabaseConnection(database, cache), database


def test_cached_database_reuses_cached_fetch_all_results() -> None:
    cached_database, database = create_cached_database()

    first = cached_database.fetch_all("select * from definitions")
    second = cached_database.fetch_all("select * from definitions")

    assert first == second
    assert database.fetch_all_calls == 1


def test_cached_database_fetch_one_uses_fetch_all_cache() -> None:
    cached_database, database = create_cached_database()

    first = cached_database.fetch_one("select * from definitions")
    second = cached_database.fetch_one("select * from definitions")

    assert first == second
    assert database.fetch_all_calls == 1


def test_cached_database_invalidates_cache_after_execute() -> None:
    cached_database, database = create_cached_database()

    cached_database.fetch_all("select * from definitions")
    cached_database.execute("update definitions set name = %s", ("new",))
    cached_database.fetch_all("select * from definitions")

    assert database.execute_calls == 1
    assert database.fetch_all_calls == 2


def test_cached_database_forwards_transaction_lifecycle_and_clears_cache() -> None:
    cached_database, database = create_cached_database()

    cached_database.fetch_all("select * from definitions")
    cached_database.begin_transaction()
    cached_database.commit()
    cached_database.fetch_all("select * from definitions")
    cached_database.begin_transaction()
    cached_database.rollback()

    assert database.commits == 1
    assert database.rollbacks == 1
    assert database.fetch_all_calls == 2


def test_cached_database_context_manager_opens_and_closes_both_layers() -> None:
    cached_database, database = create_cached_database()
    cache = cached_database.cache

    with cached_database:
        assert database.is_connected is True
        assert cache.is_connected is True
        assert cached_database.is_connected is True

    assert database.is_connected is False
    assert cache.is_connected is False
    assert cached_database.is_connected is False
