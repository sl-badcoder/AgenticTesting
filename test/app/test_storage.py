import sqlite3

import pytest

from src.app.storage import AppDatabase, UserPreferences


def create_database(tmp_path) -> AppDatabase:
    return AppDatabase(
        database_path=tmp_path / "app.db",
        secret_key_path=tmp_path / "secret.key",
    )


def test_app_database_creates_and_authenticates_user(tmp_path) -> None:
    database = create_database(tmp_path)

    user = database.create_user("senad", "password-123")

    assert database.has_users() is True
    assert database.authenticate_user("senad", "password-123") == user
    assert database.authenticate_user("senad", "bad-password") is None


def test_app_database_rejects_duplicate_user(tmp_path) -> None:
    database = create_database(tmp_path)
    database.create_user("senad", "password-123")

    with pytest.raises(ValueError, match="Username already exists"):
        database.create_user("senad", "password-456")


def test_app_database_stores_password_hash_not_plain_text(tmp_path) -> None:
    database = create_database(tmp_path)
    database.create_user("senad", "password-123")

    connection = sqlite3.connect(tmp_path / "app.db")
    stored_hash = connection.execute("select password_hash from users").fetchone()[0]

    assert stored_hash != "password-123"
    assert "password-123" not in stored_hash


def test_app_database_saves_preferences_and_encrypted_api_key(tmp_path) -> None:
    database = create_database(tmp_path)
    user = database.create_user("senad", "password-123")
    preferences = UserPreferences(
        last_repo_path="/tmp/project",
        target_coverage=88,
        project_profile="dotnet",
        test_framework="xUnit",
        provider="openai",
        model="gpt-test",
    )

    database.save_preferences(user.id, preferences)
    database.save_api_key(user.id, "openai", "sk-secret")

    loaded = database.get_preferences(user.id)
    assert loaded.last_repo_path == "/tmp/project"
    assert loaded.target_coverage == 88
    assert loaded.project_profile == "dotnet"
    assert loaded.test_framework == "xUnit"
    assert loaded.provider == "openai"
    assert loaded.model == "gpt-test"
    assert database.get_api_key(user.id, "openai") == "sk-secret"

    connection = sqlite3.connect(tmp_path / "app.db")
    encrypted = connection.execute(
        "select encrypted_api_key from api_credentials"
    ).fetchone()[0]
    assert encrypted != "sk-secret"


def test_app_database_records_run_history(tmp_path) -> None:
    database = create_database(tmp_path)
    user = database.create_user("senad", "password-123")

    database.add_run_history(
        user_id=user.id,
        repo_path="/tmp/project",
        target_coverage=80,
        final_coverage=83,
        provider="fake",
        reached_target=True,
    )

    history = database.list_run_history(user.id)

    assert len(history) == 1
    assert history[0].repo_path == "/tmp/project"
    assert history[0].reached_target is True
