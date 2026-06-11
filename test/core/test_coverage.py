import pytest

from src.core.coverage import CoverageError, CoverageRunner, parse_line_coverage
from src.core.workspace import CommandResult


class FakeWorkspace:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[str] = []

    def run_command(self, command: str) -> CommandResult:
        self.commands.append(command)
        return self.result


def test_parse_line_coverage_from_total_line() -> None:
    output = """
Name              Stmts   Miss  Cover
-------------------------------------
src/example.py       10      2    80%
-------------------------------------
TOTAL                10      2    80%
"""

    assert parse_line_coverage(output) == 80


def test_parse_line_coverage_from_jest_output() -> None:
    output = "All files |   87.5 |    100 |    75 |   87.5 |"

    assert parse_line_coverage(output) == 88


def test_parse_line_coverage_from_coverlet_output() -> None:
    output = "Line   | 76.2%"

    assert parse_line_coverage(output) == 76


def test_parse_line_coverage_from_generic_output() -> None:
    output = "Line coverage: 91%"

    assert parse_line_coverage(output) == 91


def test_parse_line_coverage_returns_none_without_total() -> None:
    assert parse_line_coverage("no coverage here") is None


def test_coverage_runner_returns_structured_report() -> None:
    workspace = FakeWorkspace(
        CommandResult(
            command="pytest --cov=.",
            exit_code=0,
            stdout="TOTAL 10 1 90%\n",
            stderr="",
        )
    )
    runner = CoverageRunner(workspace, command="pytest --cov=.")

    report = runner.run()

    assert report.line_coverage == 90
    assert report.passed is True
    assert workspace.commands == ["pytest --cov=."]


def test_coverage_runner_raises_when_coverage_cannot_be_parsed() -> None:
    workspace = FakeWorkspace(
        CommandResult(command="pytest --cov=.", exit_code=1, stdout="", stderr="failed")
    )
    runner = CoverageRunner(workspace, command="pytest --cov=.")

    with pytest.raises(CoverageError, match="Could not parse line coverage"):
        runner.run()
