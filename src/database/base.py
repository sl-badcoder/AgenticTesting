from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

QueryParameters = Mapping[str, Any] | Sequence[Any] | None
QueryResult = list[dict[str, Any]]


@dataclass(frozen=True)
class DatabaseConfig:
    vendor: str
    database: str
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


class DatabaseConnection(ABC):
    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self._connection: Any | None = None

    @abstractmethod
    def connect(self) -> None:
        """Open the underlying database connection."""

    @abstractmethod
    def close(self) -> None:
        """Close the underlying database connection."""

    @abstractmethod
    def execute(self, query: str, parameters: QueryParameters = None) -> int:
        """Execute a statement and return the number of affected rows."""

    @abstractmethod
    def fetch_one(
        self,
        query: str,
        parameters: QueryParameters = None,
    ) -> dict[str, Any] | None:
        """Execute a query and return the first row, if any."""

    @abstractmethod
    def fetch_all(
        self,
        query: str,
        parameters: QueryParameters = None,
    ) -> QueryResult:
        """Execute a query and return all rows."""

    @abstractmethod
    def begin_transaction(self) -> None:
        """Start a transaction."""

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Roll back the current transaction."""

    def __enter__(self) -> "DatabaseConnection":
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None

