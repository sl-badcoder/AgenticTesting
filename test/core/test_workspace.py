import pytest

from src.core.workspace import RepositoryWorkspace, WorkspaceError


def test_workspace_lists_and_reads_files(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text("print('hello')", encoding="utf-8")

    workspace = RepositoryWorkspace(tmp_path)

    assert workspace.list_files() == ["src/example.py"]
    assert workspace.read_file("src/example.py") == "print('hello')"


def test_workspace_rejects_path_escape(tmp_path) -> None:
    workspace = RepositoryWorkspace(tmp_path)

    with pytest.raises(WorkspaceError, match="escapes the workspace root"):
        workspace.read_file("../outside.py")


def test_workspace_replaces_exactly_one_match(tmp_path) -> None:
    (tmp_path / "module.py").write_text("value = 1\n", encoding="utf-8")
    workspace = RepositoryWorkspace(tmp_path)

    workspace.replace_text("module.py", "value = 1", "value = 2")

    assert (tmp_path / "module.py").read_text(encoding="utf-8") == "value = 2\n"


def test_workspace_rejects_ambiguous_replacement(tmp_path) -> None:
    (tmp_path / "module.py").write_text("value\nvalue\n", encoding="utf-8")
    workspace = RepositoryWorkspace(tmp_path)

    with pytest.raises(WorkspaceError, match="Expected exactly one match"):
        workspace.replace_text("module.py", "value", "updated")


def test_workspace_restricts_commands(tmp_path) -> None:
    workspace = RepositoryWorkspace(tmp_path, allowed_commands=("pytest",))

    with pytest.raises(WorkspaceError, match="not allowed"):
        workspace.run_command("python --version")
