from typing import Any

from src.database.base import DatabaseConfig, DatabaseConnection, QueryParameters, QueryResult
from src.database.exceptions import DatabaseConnectionError


class PostgresConnection(DatabaseConnection):
    def __init__(self, config: DatabaseConfig) -> None:
        super().__init__(config)
        self._transaction_open = False

    def connect(self) -> None:
        if self.is_connected:
            return

        try:
            import psycopg
        except ImportError as error:
            raise DatabaseConnectionError(
                "PostgreSQL support requires the 'psycopg' package."
            ) from error

        connection_options = {
            "dbname": self.config.database,
            "host": self.config.host,
            "port": self.config.port,
            "user": self.config.username,
            "password": self.config.password,
            **self.config.options,
        }
        connection_options = {
            key: value for key, value in connection_options.items() if value is not None
        }

        try:
            self._connection = psycopg.connect(**connection_options)
        except Exception as error:
            raise DatabaseConnectionError("Could not connect to PostgreSQL.") from error

    def close(self) -> None:
        if not self.is_connected:
            return

        self._connection.close()
        self._connection = None
        self._transaction_open = False

    def execute(self, query: str, parameters: QueryParameters = None) -> int:
        self._ensure_connected()
        with self._connection.cursor() as cursor:
            cursor.execute(query, parameters)
            row_count = cursor.rowcount
        self._commit_if_needed()
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
        with self._connection.cursor() as cursor:
            cursor.execute(query, parameters)
            column_names = [column.name for column in cursor.description or []]
            return [dict(zip(column_names, row)) for row in cursor.fetchall()]

    def begin_transaction(self) -> None:
        self._ensure_connected()
        self._transaction_open = True

    def commit(self) -> None:
        self._ensure_connected()
        self._connection.commit()
        self._transaction_open = False

    def rollback(self) -> None:
        self._ensure_connected()
        self._connection.rollback()
        self._transaction_open = False

    def _ensure_connected(self) -> None:
        if not self.is_connected:
            self.connect()

    def _commit_if_needed(self) -> None:
        if not self._transaction_open:
            self._connection.commit()
