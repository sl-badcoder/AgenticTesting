import sys
import types
from typing import Any

import pytest

from src.database.cache import CacheConfig
from src.database.cache.vendor.redis import RedisCacheConnection
from src.database.exceptions import DatabaseConnectionError


class FakeRedisClient:
    def __init__(self, **options: Any) -> None:
        self.options = options
        self.store: dict[str, str] = {}
        self.closed = False
        self.pinged = False

    def ping(self) -> None:
        self.pinged = True

    def close(self) -> None:
        self.closed = True

    def get(self, name: str) -> str | None:
        return self.store.get(name)

    def set(self, name: str, value: str, ex: int | None = None) -> None:
        self.store[name] = value

    def delete(self, *names: str) -> None:
        for name in names:
            self.store.pop(name, None)

    def scan_iter(self, match: str) -> list[str]:
        prefix = match.removesuffix("*")
        return [key for key in self.store if key.startswith(prefix)]


def install_fake_redis(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def redis_factory(**options: Any) -> FakeRedisClient:
        client = FakeRedisClient(**options)
        captured["client"] = client
        captured["options"] = options
        return client

    redis_module = types.SimpleNamespace(Redis=redis_factory)
    monkeypatch.setitem(sys.modules, "redis", redis_module)
    return captured


def test_redis_connect_passes_filtered_config_to_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = install_fake_redis(monkeypatch)
    cache = RedisCacheConnection(
        CacheConfig(
            vendor="redis",
            host="localhost",
            port=6379,
            database=1,
            username="default",
            password=None,
            options={"socket_timeout": 2},
        )
    )

    cache.connect()

    assert captured["options"] == {
        "host": "localhost",
        "port": 6379,
        "db": 1,
        "username": "default",
        "decode_responses": True,
        "socket_timeout": 2,
    }
    assert captured["client"].pinged is True


def test_redis_cache_get_set_delete_clear_and_close(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = install_fake_redis(monkeypatch)
    cache = RedisCacheConnection(CacheConfig(vendor="redis", namespace="test"))

    cache.set("first", {"value": 1})
    cache.set("second", ["a", "b"])

    assert cache.get("first") == {"value": 1}

    cache.delete("first")
    assert cache.get("first") is None

    cache.clear()
    assert cache.get("second") is None

    cache.close()
    assert captured["client"].closed is True
    assert cache.is_connected is False


def test_redis_missing_driver_raises_database_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "redis", None)
    cache = RedisCacheConnection(CacheConfig(vendor="redis"))

    with pytest.raises(DatabaseConnectionError):
        cache.connect()
