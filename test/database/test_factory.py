import pytest

from src.database.base import DatabaseConfig
from src.database.exceptions import UnsupportedDatabaseVendorError
from src.database.factory import create_database_connection
from src.database.vendor.mysql import MySQLConnection
from src.database.vendor.postgres import PostgresConnection
from src.database.vendor.sqlite import SQLiteConnection


@pytest.mark.parametrize(
    ("vendor", "expected_type"),
    [
        ("postgres", PostgresConnection),
        ("postgresql", PostgresConnection),
        ("sqlite", SQLiteConnection),
        ("mysql", MySQLConnection),
        ("mariadb", MySQLConnection),
    ],
)
def test_create_database_connection_returns_vendor_adapter(
    vendor: str,
    expected_type: type,
) -> None:
    config = DatabaseConfig(vendor=vendor, database="agentic_testing")

    connection = create_database_connection(config)

    assert isinstance(connection, expected_type)


def test_create_database_connection_rejects_unsupported_vendor() -> None:
    config = DatabaseConfig(vendor="oracle", database="agentic_testing")

    with pytest.raises(UnsupportedDatabaseVendorError):
        create_database_connection(config)
