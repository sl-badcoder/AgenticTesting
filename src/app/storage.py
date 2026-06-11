import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.app.security import FernetSecretBox, hash_password, verify_password


@dataclass(frozen=True)
class User:
    id: int
    username: str


@dataclass(frozen=True)
class UserPreferences:
    last_repo_path: str = ""
    target_coverage: int = 80
    project_profile: str = "python-pytest"
    test_framework: str = ""
    provider: str = "fake"
    model: str = ""
    model_path: str = ""
    model_id: str = ""
    device: str = ""
    coverage_command: str = "pytest --cov=. --cov-report=term-missing"
    max_iterations: int = 5


@dataclass(frozen=True)
class RunHistoryEntry:
    id: int
    repo_path: str
    target_coverage: int
    final_coverage: int
    provider: str
    reached_target: bool
    created_at: str


class AppDatabase:
    def __init__(
        self,
        database_path: str | Path = ".agentic_testing/app.db",
        secret_key_path: str | Path | None = None,
    ) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        key_path = secret_key_path or self.database_path.parent / "secret.key"
        self.secret_box = FernetSecretBox(key_path)
        self._initialize()

    def create_user(self, username: str, password: str) -> User:
        username = username.strip()
        if not username:
            raise ValueError("Username is required.")
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        password_hash = hash_password(password)
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "insert into users (username, password_hash) values (?, ?)",
                    (username, password_hash),
                )
                user_id = int(cursor.lastrowid)
                connection.execute(
                    "insert into user_preferences (user_id) values (?)",
                    (user_id,),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("Username already exists.") from error

        return User(id=user_id, username=username)

    def authenticate_user(self, username: str, password: str) -> User | None:
        row = self._fetch_one(
            "select id, username, password_hash from users where username = ?",
            (username.strip(),),
        )
        if row is None:
            return None
        if not verify_password(password, row["password_hash"]):
            return None
        return User(id=row["id"], username=row["username"])

    def get_first_user(self) -> User | None:
        row = self._fetch_one("select id, username from users order by id limit 1")
        return User(id=row["id"], username=row["username"]) if row else None

    def has_users(self) -> bool:
        row = self._fetch_one("select count(*) as user_count from users")
        return bool(row and row["user_count"])

    def get_preferences(self, user_id: int) -> UserPreferences:
        row = self._fetch_one(
            "select * from user_preferences where user_id = ?",
            (user_id,),
        )
        if row is None:
            return UserPreferences()

        return UserPreferences(
            last_repo_path=row["last_repo_path"] or "",
            target_coverage=row["target_coverage"],
            project_profile=row["project_profile"] or "python-pytest",
            test_framework=row["test_framework"] or "",
            provider=row["provider"],
            model=row["model"] or "",
            model_path=row["model_path"] or "",
            model_id=row["model_id"] or "",
            device=row["device"] or "",
            coverage_command=row["coverage_command"],
            max_iterations=row["max_iterations"],
        )

    def save_preferences(self, user_id: int, preferences: UserPreferences) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                insert into user_preferences (
                    user_id,
                    last_repo_path,
                    target_coverage,
                    project_profile,
                    test_framework,
                    provider,
                    model,
                    model_path,
                    model_id,
                    device,
                    coverage_command,
                    max_iterations
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(user_id) do update set
                    last_repo_path = excluded.last_repo_path,
                    target_coverage = excluded.target_coverage,
                    project_profile = excluded.project_profile,
                    test_framework = excluded.test_framework,
                    provider = excluded.provider,
                    model = excluded.model,
                    model_path = excluded.model_path,
                    model_id = excluded.model_id,
                    device = excluded.device,
                    coverage_command = excluded.coverage_command,
                    max_iterations = excluded.max_iterations
                """,
                (
                    user_id,
                    preferences.last_repo_path,
                    preferences.target_coverage,
                    preferences.project_profile,
                    preferences.test_framework,
                    preferences.provider,
                    preferences.model,
                    preferences.model_path,
                    preferences.model_id,
                    preferences.device,
                    preferences.coverage_command,
                    preferences.max_iterations,
                ),
            )

    def save_api_key(self, user_id: int, provider: str, api_key: str) -> None:
        api_key = api_key.strip()
        if not api_key:
            return

        encrypted = self.secret_box.encrypt(api_key)
        with self._connect() as connection:
            connection.execute(
                """
                insert into api_credentials (user_id, provider, encrypted_api_key)
                values (?, ?, ?)
                on conflict(user_id, provider) do update set
                    encrypted_api_key = excluded.encrypted_api_key,
                    updated_at = current_timestamp
                """,
                (user_id, provider, encrypted),
            )

    def get_api_key(self, user_id: int, provider: str) -> str | None:
        row = self._fetch_one(
            """
            select encrypted_api_key from api_credentials
            where user_id = ? and provider = ?
            """,
            (user_id, provider),
        )
        if row is None:
            return None
        return self.secret_box.decrypt(row["encrypted_api_key"])

    def has_api_key(self, user_id: int, provider: str) -> bool:
        row = self._fetch_one(
            """
            select 1 from api_credentials
            where user_id = ? and provider = ?
            """,
            (user_id, provider),
        )
        return row is not None

    def add_run_history(
        self,
        user_id: int,
        repo_path: str,
        target_coverage: int,
        final_coverage: int,
        provider: str,
        reached_target: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                insert into run_history (
                    user_id,
                    repo_path,
                    target_coverage,
                    final_coverage,
                    provider,
                    reached_target
                )
                values (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    repo_path,
                    target_coverage,
                    final_coverage,
                    provider,
                    int(reached_target),
                ),
            )

    def list_run_history(self, user_id: int, limit: int = 5) -> list[RunHistoryEntry]:
        rows = self._fetch_all(
            """
            select id, repo_path, target_coverage, final_coverage, provider,
                   reached_target, created_at
            from run_history
            where user_id = ?
            order by id desc
            limit ?
            """,
            (user_id, limit),
        )
        return [
            RunHistoryEntry(
                id=row["id"],
                repo_path=row["repo_path"],
                target_coverage=row["target_coverage"],
                final_coverage=row["final_coverage"],
                provider=row["provider"],
                reached_target=bool(row["reached_target"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                create table if not exists users (
                    id integer primary key autoincrement,
                    username text not null unique,
                    password_hash text not null,
                    created_at text not null default current_timestamp
                );

                create table if not exists user_preferences (
                    user_id integer primary key,
                    last_repo_path text not null default '',
                    target_coverage integer not null default 80,
                    project_profile text not null default 'python-pytest',
                    test_framework text not null default '',
                    provider text not null default 'fake',
                    model text not null default '',
                    model_path text not null default '',
                    model_id text not null default '',
                    device text not null default '',
                    coverage_command text not null default 'pytest --cov=. --cov-report=term-missing',
                    max_iterations integer not null default 5,
                    foreign key (user_id) references users(id) on delete cascade
                );

                create table if not exists api_credentials (
                    user_id integer not null,
                    provider text not null,
                    encrypted_api_key text not null,
                    updated_at text not null default current_timestamp,
                    primary key (user_id, provider),
                    foreign key (user_id) references users(id) on delete cascade
                );

                create table if not exists run_history (
                    id integer primary key autoincrement,
                    user_id integer not null,
                    repo_path text not null,
                    target_coverage integer not null,
                    final_coverage integer not null,
                    provider text not null,
                    reached_target integer not null,
                    created_at text not null default current_timestamp,
                    foreign key (user_id) references users(id) on delete cascade
                );
                """
            )
            self._ensure_column(
                connection,
                "user_preferences",
                "project_profile",
                "text not null default 'python-pytest'",
            )
            self._ensure_column(
                connection,
                "user_preferences",
                "test_framework",
                "text not null default ''",
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("pragma foreign_keys = on")
        return connection

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"pragma table_info({table})").fetchall()
        }
        if column not in columns:
            connection.execute(f"alter table {table} add column {column} {definition}")

    def _fetch_one(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(query, parameters).fetchone()

    def _fetch_all(
        self,
        query: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return list(connection.execute(query, parameters).fetchall())
