import sqlite3
from typing import Any

from src.database.base import DatabaseConfig, DatabaseConnection, QueryParameters, QueryResult
from src.database.exceptions import DatabaseConnectionError


class SQLiteConnection(DatabaseConnection):
    def __init__(self, config: DatabaseConfig) -> None:
        super().__init__(config)
        self._transaction_open = False

    def connect(self) -> None:
        if self.is_connected:
            return

        try:
            self._connection = sqlite3.connect(
                self.config.database,
                **self.config.options,
            )
            self._connection.row_factory = sqlite3.Row
        except sqlite3.Error as error:
            raise DatabaseConnectionError("Could not connect to SQLite.") from error

    def close(self) -> None:
        if not self.is_connected:
            return

        self._connection.close()
        self._connection = None
        self._transaction_open = False

    def execute(self, query: str, parameters: QueryParameters = None) -> int:
        self._ensure_connected()
        cursor = self._connection.execute(query, parameters or ())
        row_count = cursor.rowcount
        self._commit_if_needed()
        return row_count

    def fetch_one(
        self,
        query: str,
        parameters: QueryParameters = None,
    ) -> dict[str, Any] | None:
        self._ensure_connected()
        cursor = self._connection.execute(query, parameters or ())
        row = cursor.fetchone()
        return dict(row) if row else None

    def fetch_all(
        self,
        query: str,
        parameters: QueryParameters = None,
    ) -> QueryResult:
        self._ensure_connected()
        cursor = self._connection.execute(query, parameters or ())
        return [dict(row) for row in cursor.fetchall()]

    def begin_transaction(self) -> None:
        self._ensure_connected()
        self._connection.execute("BEGIN")
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

