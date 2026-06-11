class DatabaseError(Exception):
    """Base exception for database infrastructure errors."""


class DatabaseConnectionError(DatabaseError):
    """Raised when a database connection cannot be opened."""


class UnsupportedDatabaseVendorError(DatabaseError):
    """Raised when no implementation exists for the configured vendor."""
