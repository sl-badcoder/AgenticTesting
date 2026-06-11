import pytest

from src.database.base import DatabaseConfig, DatabaseConnection


def test_database_connection_cannot_be_instantiated_directly() -> None:
    config = DatabaseConfig(vendor="sqlite", database=":memory:")

    with pytest.raises(TypeError):
        DatabaseConnection(config)


def test_database_config_uses_independent_options_dicts() -> None:
    first = DatabaseConfig(vendor="sqlite", database="first.db")
    second = DatabaseConfig(vendor="sqlite", database="second.db")

    first.options["timeout"] = 10

    assert second.options == {}
