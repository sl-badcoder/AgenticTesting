from src.database.cache.base import CacheConfig, CacheConnection
from src.database.cache.vendor.in_memory import InMemoryCacheConnection
from src.database.cache.vendor.redis import RedisCacheConnection
from src.database.exceptions import UnsupportedDatabaseVendorError


def create_cache_connection(config: CacheConfig) -> CacheConnection:
    vendor = config.vendor.lower()

    if vendor in {"memory", "in-memory", "in_memory"}:
        return InMemoryCacheConnection(config)

    if vendor == "redis":
        return RedisCacheConnection(config)

    raise UnsupportedDatabaseVendorError(
        f"Unsupported cache vendor '{config.vendor}'."
    )
