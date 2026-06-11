import asyncio

from src.core.agentic_testing import AgenticTestingConfig, AgenticTestingRunner
from src.core.coverage import CoverageReport
from src.core.workspace import CommandResult, RepositoryWorkspace
from src.frontend.llm.fake import FakeLLMProvider


class FakeCoverageRunner:
    def __init__(self, coverages: list[int]) -> None:
        self.coverages = coverages
        self.calls = 0

    def run(self) -> CoverageReport:
        coverage = self.coverages[min(self.calls, len(self.coverages) - 1)]
        self.calls += 1
        return CoverageReport(
            line_coverage=coverage,
            command_result=CommandResult(
                command="pytest --cov=.",
                exit_code=0,
                stdout=f"TOTAL 10 {10 - coverage // 10} {coverage}%\n",
                stderr="",
            ),
            raw_output=f"TOTAL 10 {10 - coverage // 10} {coverage}%\n",
        )


def test_agentic_testing_runner_stops_when_initial_coverage_reaches_target(tmp_path) -> None:
    provider = FakeLLMProvider()
    workspace = RepositoryWorkspace(tmp_path)
    runner = AgenticTestingRunner(
        config=AgenticTestingConfig(
            repository_path=tmp_path,
            target_line_coverage=80,
        ),
        provider=provider,
        workspace=workspace,
        coverage_runner=FakeCoverageRunner([85]),
    )

    result = asyncio.run(runner.run())

    assert result.reached_target is True
    assert result.final_line_coverage == 85
    assert result.iterations == []


def test_agentic_testing_runner_runs_agent_sequence_until_target(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text("def add(a, b):\n    return a + b\n")
    provider = FakeLLMProvider(
        responses=[
            "Analyze uncovered add function.",
            "Add a unit test for add.",
            '{"actions": [], "final": "No-op fake implementation."}',
            "Review complete.",
        ]
    )
    workspace = RepositoryWorkspace(tmp_path)
    runner = AgenticTestingRunner(
        config=AgenticTestingConfig(
            repository_path=tmp_path,
            target_line_coverage=80,
            max_iterations=2,
        ),
        provider=provider,
        workspace=workspace,
        coverage_runner=FakeCoverageRunner([40, 82]),
    )

    result = asyncio.run(runner.run())

    assert result.reached_target is True
    assert result.final_line_coverage == 82
    assert len(result.iterations) == 1
    assert result.iterations[0].starting_coverage == 40
    assert result.iterations[0].analyzer_summary == "Analyze uncovered add function."
    assert result.iterations[0].plan == "Add a unit test for add."
    assert result.iterations[0].reviewer_feedback == "Review complete."
