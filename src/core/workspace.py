import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


class WorkspaceError(Exception):
    """Raised when a workspace operation is invalid or unsafe."""


@dataclass(frozen=True)
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


class RepositoryWorkspace:
    def __init__(
        self,
        root: str | Path,
        allowed_commands: tuple[str, ...] = ("pytest",),
        command_timeout_seconds: int = 120,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists() or not self.root.is_dir():
            raise WorkspaceError(f"Workspace root '{self.root}' is not a directory.")

        self.allowed_commands = allowed_commands
        self.command_timeout_seconds = command_timeout_seconds

    def list_files(self) -> list[str]:
        files: list[str] = []
        for path in self.root.rglob("*"):
            if self._should_skip(path) or not path.is_file():
                continue
            files.append(path.relative_to(self.root).as_posix())
        return sorted(files)

    def read_file(self, relative_path: str) -> str:
        path = self._resolve_path(relative_path)
        if not path.is_file():
            raise WorkspaceError(f"'{relative_path}' is not a file.")
        return path.read_text(encoding="utf-8")

    def write_file(self, relative_path: str, content: str) -> str:
        path = self._resolve_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {relative_path}."

    def replace_text(self, relative_path: str, old: str, new: str) -> str:
        if old == "":
            raise WorkspaceError("Replacement text cannot be empty.")

        content = self.read_file(relative_path)
        occurrences = content.count(old)
        if occurrences != 1:
            raise WorkspaceError(
                f"Expected exactly one match in '{relative_path}', found {occurrences}."
            )

        updated = content.replace(old, new, 1)
        return self.write_file(relative_path, updated)

    def run_command(self, command: str) -> CommandResult:
        args = shlex.split(command)
        if not args:
            raise WorkspaceError("Command cannot be empty.")

        if args[0] not in self.allowed_commands:
            raise WorkspaceError(
                f"Command '{args[0]}' is not allowed. "
                f"Allowed commands: {', '.join(self.allowed_commands)}."
            )

        try:
            completed = subprocess.run(
                args,
                cwd=self.root,
                text=True,
                capture_output=True,
                timeout=self.command_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise WorkspaceError(
                f"Command timed out after {self.command_timeout_seconds} seconds."
            ) from error

        return CommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _resolve_path(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if path != self.root and self.root not in path.parents:
            raise WorkspaceError(f"Path '{relative_path}' escapes the workspace root.")
        return path

    def _should_skip(self, path: Path) -> bool:
        ignored_parts = {".git", ".venv", "__pycache__", ".pytest_cache"}
        return any(part in ignored_parts for part in path.relative_to(self.root).parts)
