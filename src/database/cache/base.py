from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CacheConfig:
    vendor: str
    host: str | None = None
    port: int | None = None
    database: int | str | None = None
    username: str | None = None
    password: str | None = None
    namespace: str = "agentic_testing"
    default_ttl_seconds: int | None = None
    options: dict[str, Any] = field(default_factory=dict)


class CacheConnection(ABC):
    def __init__(self, config: CacheConfig) -> None:
        self.config = config
        self._connection: Any | None = None

    @abstractmethod
    def connect(self) -> None:
        """Open the underlying cache connection."""

    @abstractmethod
    def close(self) -> None:
        """Close the underlying cache connection."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return a cached value, or None when the key is absent."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Store a value in the cache."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete one cached value."""

    @abstractmethod
    def clear(self) -> None:
        """Clear values belonging to this cache namespace."""

    def __enter__(self) -> "CacheConnection":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None

    def namespaced_key(self, key: str) -> str:
        return f"{self.config.namespace}:{key}"
