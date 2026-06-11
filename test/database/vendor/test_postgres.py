import sys
import types
from dataclasses import dataclass
from typing import Any

import pytest

from src.database.base import DatabaseConfig
from src.database.exceptions import DatabaseConnectionError
from src.database.vendor.postgres import PostgresConnection


@dataclass
class FakeColumn:
    name: str


class FakePostgresCursor:
    def __init__(self) -> None:
        self.description = [FakeColumn("id"), FakeColumn("name")]
        self.rowcount = 2
        self.executed: list[tuple[str, Any]] = []

    def __enter__(self) -> "FakePostgresCursor":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def execute(self, query: str, parameters: Any = None) -> None:
        self.executed.append((query, parameters))

    def fetchall(self) -> list[tuple[int, str]]:
        return [(1, "coverage"), (2, "users")]


class FakePostgresConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakePostgresCursor()
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def cursor(self) -> FakePostgresCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def install_fake_psycopg(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    fake_connection = FakePostgresConnection()
    captured_options: dict[str, Any] = {}

    def connect(**options: Any) -> FakePostgresConnection:
        captured_options.update(options)
        return fake_connection

    fake_psycopg = types.SimpleNamespace(connect=connect)
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    return {"connection": fake_connection, "options": captured_options}


def test_postgres_connect_passes_filtered_config_to_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = install_fake_psycopg(monkeypatch)
    connection = PostgresConnection(
        DatabaseConfig(
            vendor="postgres",
            database="agentic_testing",
            host="localhost",
            port=5432,
            username="postgres",
            password=None,
            options={"connect_timeout": 5},
        )
    )

    connection.connect()

    assert fake["options"] == {
        "dbname": "agentic_testing",
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "connect_timeout": 5,
    }


def test_postgres_execute_fetch_and_transaction_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = install_fake_psycopg(monkeypatch)
    fake_connection = fake["connection"]
    connection = PostgresConnection(DatabaseConfig(vendor="postgres", database="db"))

    row_count = connection.execute("update definitions set name = %s", ("coverage",))

    assert row_count == 2
    assert fake_connection.commits == 1
    assert connection.fetch_all("select id, name from definitions") == [
        {"id": 1, "name": "coverage"},
        {"id": 2, "name": "users"},
    ]
    assert connection.fetch_one("select id, name from definitions") == {
        "id": 1,
        "name": "coverage",
    }

    connection.begin_transaction()
    connection.execute("delete from definitions")
    assert fake_connection.commits == 1

    connection.commit()
    assert fake_connection.commits == 2

    connection.begin_transaction()
    connection.rollback()
    assert fake_connection.rollbacks == 1

    connection.close()
    assert fake_connection.closed is True
    assert connection.is_connected is False


def test_postgres_missing_driver_raises_database_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "psycopg", None)
    connection = PostgresConnection(DatabaseConfig(vendor="postgres", database="db"))

    with pytest.raises(DatabaseConnectionError):
        connection.connect()
