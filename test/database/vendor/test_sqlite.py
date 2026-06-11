from pathlib import Path

from src.database.base import DatabaseConfig
from src.database.vendor.sqlite import SQLiteConnection


def create_connection(database: Path | str = ":memory:") -> SQLiteConnection:
    return SQLiteConnection(DatabaseConfig(vendor="sqlite", database=str(database)))


def test_sqlite_execute_and_fetch_methods_return_dict_rows() -> None:
    connection = create_connection()

    connection.execute("create table definitions (id integer primary key, name text)")
    connection.execute(
        "insert into definitions (name) values (?)",
        ("coverage-goal",),
    )

    assert connection.fetch_one("select name from definitions") == {
        "name": "coverage-goal",
    }
    assert connection.fetch_all("select id, name from definitions") == [
        {"id": 1, "name": "coverage-goal"},
    ]

    connection.close()


def test_sqlite_context_manager_opens_and_closes_connection() -> None:
    connection = create_connection()

    with connection as active_connection:
        assert active_connection.is_connected is True

    assert connection.is_connected is False


def test_sqlite_rollback_discards_open_transaction() -> None:
    connection = create_connection()
    connection.execute("create table definitions (id integer primary key, name text)")

    connection.begin_transaction()
    connection.execute(
        "insert into definitions (name) values (?)",
        ("temporary",),
    )
    connection.rollback()

    assert connection.fetch_all("select * from definitions") == []

    connection.close()


def test_sqlite_file_database_can_be_reopened(tmp_path: Path) -> None:
    database_path = tmp_path / "agentic_testing.sqlite3"
    connection = create_connection(database_path)

    connection.execute("create table users (id integer primary key, email text)")
    connection.execute("insert into users (email) values (?)", ("user@example.com",))
    connection.close()

    reopened = create_connection(database_path)

    assert reopened.fetch_one("select email from users") == {
        "email": "user@example.com",
    }

    reopened.close()
