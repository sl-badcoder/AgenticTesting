import sys
import types
from typing import Any

import pytest

from src.database.base import DatabaseConfig
from src.database.exceptions import DatabaseConnectionError
from src.database.vendor.mysql import MySQLConnection


class FakeMySQLCursor:
    def __init__(self) -> None:
        self.rowcount = 3
        self.closed = False
        self.executed: list[tuple[str, Any]] = []

    def execute(self, query: str, parameters: Any = None) -> None:
        self.executed.append((query, parameters))

    def fetchall(self) -> list[dict[str, Any]]:
        return [
            {"id": 1, "name": "coverage"},
            {"id": 2, "name": "users"},
        ]

    def close(self) -> None:
        self.closed = True


class FakeMySQLConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeMySQLCursor()
        self.commits = 0
        self.rollbacks = 0
        self.started_transactions = 0
        self.closed = False

    def cursor(self, dictionary: bool = False) -> FakeMySQLCursor:
        return self.cursor_instance

    def start_transaction(self) -> None:
        self.started_transactions += 1

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closed = True


def install_fake_mysql_connector(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    fake_connection = FakeMySQLConnection()
    captured_options: dict[str, Any] = {}

    def connect(**options: Any) -> FakeMySQLConnection:
        captured_options.update(options)
        return fake_connection

    connector_module = types.SimpleNamespace(connect=connect)
    mysql_module = types.SimpleNamespace(connector=connector_module)
    monkeypatch.setitem(sys.modules, "mysql", mysql_module)
    monkeypatch.setitem(sys.modules, "mysql.connector", connector_module)
    return {"connection": fake_connection, "options": captured_options}


def test_mysql_connect_passes_filtered_config_to_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = install_fake_mysql_connector(monkeypatch)
    connection = MySQLConnection(
        DatabaseConfig(
            vendor="mysql",
            database="agentic_testing",
            host="localhost",
            port=3306,
            username="root",
            password=None,
            options={"connection_timeout": 5},
        )
    )

    connection.connect()

    assert fake["options"] == {
        "database": "agentic_testing",
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "connection_timeout": 5,
    }


def test_mysql_execute_fetch_and_transaction_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = install_fake_mysql_connector(monkeypatch)
    fake_connection = fake["connection"]
    connection = MySQLConnection(DatabaseConfig(vendor="mysql", database="db"))

    row_count = connection.execute("update definitions set name = %s", ("coverage",))

    assert row_count == 3
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
    assert fake_connection.started_transactions == 1
    assert fake_connection.commits == 1

    connection.commit()
    assert fake_connection.commits == 2

    connection.begin_transaction()
    connection.rollback()
    assert fake_connection.rollbacks == 1

    connection.close()
    assert fake_connection.closed is True
    assert connection.is_connected is False


def test_mysql_missing_driver_raises_database_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "mysql", None)
    monkeypatch.setitem(sys.modules, "mysql.connector", None)
    connection = MySQLConnection(DatabaseConfig(vendor="mysql", database="db"))

    with pytest.raises(DatabaseConnectionError):
        connection.connect()
