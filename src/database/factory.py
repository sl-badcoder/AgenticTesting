from src.database.base import DatabaseConfig, DatabaseConnection
from src.database.exceptions import UnsupportedDatabaseVendorError
from src.database.vendor.mysql import MySQLConnection
from src.database.vendor.postgres import PostgresConnection
from src.database.vendor.sqlite import SQLiteConnection


def create_database_connection(config: DatabaseConfig) -> DatabaseConnection:
    vendor = config.vendor.lower()

    if vendor in {"postgres", "postgresql"}:
        return PostgresConnection(config)

    if vendor == "sqlite":
        return SQLiteConnection(config)

    if vendor in {"mysql", "mariadb"}:
        return MySQLConnection(config)

    raise UnsupportedDatabaseVendorError(
        f"Unsupported database vendor '{config.vendor}'."
    )
