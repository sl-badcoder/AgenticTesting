import time

from src.database.cache import CacheConfig
from src.database.cache.vendor.in_memory import InMemoryCacheConnection


def test_in_memory_cache_get_set_delete_and_clear() -> None:
    cache = InMemoryCacheConnection(CacheConfig(vendor="memory", namespace="test"))

    cache.set("first", {"value": 1})
    cache.set("second", ["a", "b"])

    assert cache.get("first") == {"value": 1}
    assert cache.get("second") == ["a", "b"]

    cache.delete("first")
    assert cache.get("first") is None

    cache.clear()
    assert cache.get("second") is None


def test_in_memory_cache_clear_only_removes_own_namespace() -> None:
    first = InMemoryCacheConnection(CacheConfig(vendor="memory", namespace="first"))
    second = InMemoryCacheConnection(CacheConfig(vendor="memory", namespace="second"))
    shared_store = {}
    first._store = shared_store
    second._store = shared_store

    first.set("key", "first-value")
    second.set("key", "second-value")

    first.clear()

    assert first.get("key") is None
    assert second.get("key") == "second-value"


def test_in_memory_cache_expires_values() -> None:
    cache = InMemoryCacheConnection(
        CacheConfig(vendor="memory", default_ttl_seconds=0)
    )

    cache.set("key", "value")
    time.sleep(0.001)

    assert cache.get("key") is None
