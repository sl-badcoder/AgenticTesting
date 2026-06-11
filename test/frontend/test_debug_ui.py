from pathlib import Path

import pytest

from src.app.storage import AppDatabase
from src.frontend.debug_ui import (
    DebugRunConfig,
    build_provider_config,
    open_native_folder_dialog,
    read_debug_config,
    read_ui_run_config,
    render_dashboard,
    render_folder_browser,
    render_page,
)


def test_read_debug_config_accepts_valid_input(tmp_path: Path) -> None:
    config = read_debug_config(
        {
            "project_folder": [str(tmp_path)],
            "coverage_percentage": ["80"],
        }
    )

    assert config == DebugRunConfig(
        project_folder=str(tmp_path),
        coverage_percentage=80,
    )


@pytest.mark.parametrize(
    ("form_data", "expected_error"),
    [
        ({}, "Project folder is required."),
        ({"project_folder": ["/missing"], "coverage_percentage": ["80"]}, "Project folder must be an existing folder."),
        ({"project_folder": ["."], "coverage_percentage": ["abc"]}, "Line coverage target must be a number."),
        ({"project_folder": ["."], "coverage_percentage": ["101"]}, "Line coverage target must be between 0 and 100."),
    ],
)
def test_read_debug_config_rejects_invalid_input(
    form_data: dict[str, list[str]],
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        read_debug_config(form_data)


def test_render_page_includes_config_json(tmp_path: Path) -> None:
    html = render_page(
        DebugRunConfig(project_folder=str(tmp_path), coverage_percentage=75)
    )

    assert str(tmp_path) in html
    assert "&quot;coverage_percentage&quot;: 75" in html


def test_read_ui_run_config_accepts_valid_input(tmp_path: Path) -> None:
    config = read_ui_run_config(
        {
            "repo_path": [str(tmp_path)],
            "target_coverage": ["82"],
            "project_profile": ["dotnet"],
            "test_framework": ["xUnit"],
            "provider": ["fake"],
            "coverage_command": [""],
            "max_iterations": ["3"],
        }
    )

    assert config.repo_path == str(tmp_path)
    assert config.target_coverage == 82
    assert config.project_profile == "dotnet"
    assert config.test_framework == "xUnit"
    assert config.provider == "fake"
    assert config.coverage_command.startswith("dotnet test")
    assert config.max_iterations == 3


def test_build_provider_config_reads_saved_api_key(tmp_path: Path) -> None:
    database = AppDatabase(
        database_path=tmp_path / "app.db",
        secret_key_path=tmp_path / "secret.key",
    )
    user = database.create_user("senad", "password-123")
    database.save_api_key(user.id, "openai", "sk-saved")
    config = read_ui_run_config(
        {
            "repo_path": [str(tmp_path)],
            "target_coverage": ["80"],
            "project_profile": ["python-pytest"],
            "provider": ["openai"],
            "model": ["gpt-test"],
            "coverage_command": ["pytest --cov=."],
            "max_iterations": ["1"],
        }
    )

    provider_config = build_provider_config(config, database, user.id)

    assert provider_config["type"] == "openai"
    assert provider_config["model"] == "gpt-test"
    assert provider_config["api_key"] == "sk-saved"


def test_render_dashboard_includes_saved_preferences(tmp_path: Path) -> None:
    database = AppDatabase(
        database_path=tmp_path / "app.db",
        secret_key_path=tmp_path / "secret.key",
    )
    user = database.create_user("senad", "password-123")

    html = render_dashboard(database, user)

    assert "Coverage workspace" in html
    assert "target_coverage" in html
    assert "Project and test stack" in html
    assert "/browse-native" in html


def test_render_folder_browser_includes_select_links(tmp_path: Path) -> None:
    child = tmp_path / "project"
    child.mkdir()

    html = render_folder_browser("", str(tmp_path))

    assert "Folder fallback" in html
    assert "project" in html
    assert "selected_repo" in html


def test_open_native_folder_dialog_falls_back_to_home_for_missing_start(monkeypatch) -> None:
    captured = {}

    def fake_macos_dialog(start: Path) -> str:
        captured["start"] = start
        return str(start)

    monkeypatch.setattr("src.frontend.debug_ui.sys.platform", "darwin")
    monkeypatch.setattr("src.frontend.debug_ui._open_macos_folder_dialog", fake_macos_dialog)

    selected = open_native_folder_dialog("/path/that/does/not/exist")

    assert selected == str(Path.home())
    assert captured["start"] == Path.home()
