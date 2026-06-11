import re
from dataclasses import dataclass

from src.core.workspace import CommandResult, RepositoryWorkspace


class CoverageError(Exception):
    """Raised when line coverage cannot be measured."""


@dataclass(frozen=True)
class CoverageReport:
    line_coverage: int
    command_result: CommandResult
    raw_output: str

    @property
    def passed(self) -> bool:
        return self.command_result.exit_code == 0


class CoverageRunner:
    def __init__(
        self,
        workspace: RepositoryWorkspace,
        command: str = "pytest --cov=. --cov-report=term-missing",
    ) -> None:
        self.workspace = workspace
        self.command = command

    def run(self) -> CoverageReport:
        result = self.workspace.run_command(self.command)
        output = f"{result.stdout}\n{result.stderr}".strip()
        coverage = parse_line_coverage(output)
        if coverage is None:
            raise CoverageError(
                "Could not parse line coverage. Make sure pytest-cov is installed "
                "and the coverage command prints a TOTAL line."
            )

        return CoverageReport(
            line_coverage=coverage,
            command_result=result,
            raw_output=output,
        )


def parse_line_coverage(output: str) -> int | None:
    patterns = [
        # pytest-cov and gcovr text reports.
        re.compile(r"^TOTAL\s+.*?\s+(\d+(?:\.\d+)?)%\s*$", re.MULTILINE),
        # Jest text table: All files | 80 | ...
        re.compile(r"^All files\s+\|\s+(\d+(?:\.\d+)?)", re.MULTILINE),
        # Coverlet summary: Line | 80%
        re.compile(r"^\s*Line\s*\|\s*(\d+(?:\.\d+)?)%", re.MULTILINE),
        # Generic fallback: Line coverage: 80%
        re.compile(r"Line coverage:?\s+(\d+(?:\.\d+)?)%", re.IGNORECASE),
    ]

    for pattern in patterns:
        match = pattern.search(output)
        if match:
            return round(float(match.group(1)))

    return None
