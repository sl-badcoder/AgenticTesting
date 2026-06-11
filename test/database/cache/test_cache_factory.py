import pytest

from src.database.cache import CacheConfig, create_cache_connection
from src.database.cache.vendor.in_memory import InMemoryCacheConnection
from src.database.cache.vendor.redis import RedisCacheConnection
from src.database.exceptions import UnsupportedDatabaseVendorError


@pytest.mark.parametrize(
    ("vendor", "expected_type"),
    [
        ("memory", InMemoryCacheConnection),
        ("in-memory", InMemoryCacheConnection),
        ("in_memory", InMemoryCacheConnection),
        ("redis", RedisCacheConnection),
    ],
)
def test_create_cache_connection_returns_vendor_adapter(
    vendor: str,
    expected_type: type,
) -> None:
    cache = create_cache_connection(CacheConfig(vendor=vendor))

    assert isinstance(cache, expected_type)


def test_create_cache_connection_rejects_unsupported_vendor() -> None:
    with pytest.raises(UnsupportedDatabaseVendorError):
        create_cache_connection(CacheConfig(vendor="memcached"))
