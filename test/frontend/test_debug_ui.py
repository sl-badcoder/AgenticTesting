from pathlib import Path

import pytest

from src.frontend.debug_ui import DebugRunConfig, read_debug_config, render_page


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
    assert '"coverage_percentage": 75' in html
