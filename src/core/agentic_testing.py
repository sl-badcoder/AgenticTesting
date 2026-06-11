from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from src.core.coverage import CoverageReport, CoverageRunner
from src.core.local_coding_agent import CodingAgentResult, LocalCodingAgent
from src.core.project_profiles import get_project_profile
from src.core.workspace import RepositoryWorkspace
from src.frontend.llm.base import LLMProvider


ANALYZER_PROMPT = """You are the analyzer in an AgenticTesting pipeline.
Summarize the current test coverage state and identify the most useful files or gaps
to inspect next. Be concise and practical.
"""

PLANNER_PROMPT = """You are the planner in an AgenticTesting pipeline.
Create a focused test-improvement plan that can be implemented in the next iteration.
Prefer small, high-value tests that raise line coverage without changing production
behavior. Return plain text, not JSON.
"""

REVIEWER_PROMPT = """You are the reviewer in an AgenticTesting pipeline.
Review the implementer's result and coverage output. Identify whether the next
iteration should fix tests, add missing assertions, or target uncovered code.
Return concise feedback.
"""


@dataclass(frozen=True)
class AgenticTestingConfig:
    repository_path: str | Path
    target_line_coverage: int
    max_iterations: int = 5
    coverage_command: str = "pytest --cov=. --cov-report=term-missing"
    allowed_commands: tuple[str, ...] = ("pytest",)
    implementer_max_steps: int = 8
    project_profile: str = "python-pytest"
    test_framework: str = ""


@dataclass(frozen=True)
class AgenticTestingIteration:
    number: int
    starting_coverage: int
    analyzer_summary: str
    plan: str
    implementation: CodingAgentResult
    reviewer_feedback: str


@dataclass(frozen=True)
class AgenticTestingResult:
    target_line_coverage: int
    final_line_coverage: int
    reached_target: bool
    iterations: list[AgenticTestingIteration] = field(default_factory=list)
    final_report: CoverageReport | None = None


ImplementerFactory = Callable[[LLMProvider, RepositoryWorkspace, int], LocalCodingAgent]


class AgenticTestingRunner:
    def __init__(
        self,
        config: AgenticTestingConfig,
        provider: LLMProvider,
        coverage_runner: CoverageRunner | None = None,
        workspace: RepositoryWorkspace | None = None,
        implementer_factory: ImplementerFactory | None = None,
    ) -> None:
        self.config = config
        self.provider = provider
        self.workspace = workspace or RepositoryWorkspace(
            root=config.repository_path,
            allowed_commands=config.allowed_commands,
        )
        self.coverage_runner = coverage_runner or CoverageRunner(
            workspace=self.workspace,
            command=config.coverage_command,
        )
        self.implementer_factory = implementer_factory or LocalCodingAgent

    async def run(self) -> AgenticTestingResult:
        iterations: list[AgenticTestingIteration] = []
        report = self.coverage_runner.run()

        for iteration_number in range(1, self.config.max_iterations + 1):
            if report.line_coverage >= self.config.target_line_coverage:
                return self._result(report, iterations)

            starting_coverage = report.line_coverage
            analyzer_summary = await self._analyze(report)
            plan = await self._plan(report, analyzer_summary)
            implementation = await self._implement(report, analyzer_summary, plan)
            report = self.coverage_runner.run()
            reviewer_feedback = await self._review(report, implementation, plan)

            iterations.append(
                AgenticTestingIteration(
                    number=iteration_number,
                    starting_coverage=starting_coverage,
                    analyzer_summary=analyzer_summary,
                    plan=plan,
                    implementation=implementation,
                    reviewer_feedback=reviewer_feedback,
                )
            )

        return self._result(report, iterations)

    async def _analyze(self, report: CoverageReport) -> str:
        prompt = (
            f"Target line coverage: {self.config.target_line_coverage}%\n"
            f"Current line coverage: {report.line_coverage}%\n"
            f"Project profile: {self._profile().label}\n"
            f"Test framework: {self._test_framework()}\n"
            f"Coverage command passed: {report.passed}\n\n"
            f"Coverage output:\n{self._trim(report.raw_output)}"
        )
        return await self.provider.generate(prompt, system_prompt=ANALYZER_PROMPT)

    async def _plan(self, report: CoverageReport, analyzer_summary: str) -> str:
        files = "\n".join(self.workspace.list_files()[:200])
        prompt = (
            f"Target line coverage: {self.config.target_line_coverage}%\n"
            f"Current line coverage: {report.line_coverage}%\n\n"
            f"Project profile: {self._profile().label}\n"
            f"Test framework: {self._test_framework()}\n"
            f"Testing guidance: {self._profile().guidance}\n\n"
            f"Analyzer summary:\n{analyzer_summary}\n\n"
            f"Repository files:\n{files}"
        )
        return await self.provider.generate(prompt, system_prompt=PLANNER_PROMPT)

    async def _implement(
        self,
        report: CoverageReport,
        analyzer_summary: str,
        plan: str,
    ) -> CodingAgentResult:
        task = (
            "Improve this repository's tests until the requested line coverage is "
            "closer to the target.\n\n"
            f"Target line coverage: {self.config.target_line_coverage}%\n"
            f"Current line coverage: {report.line_coverage}%\n\n"
            f"Project profile: {self._profile().label}\n"
            f"Test framework: {self._test_framework()}\n"
            f"Testing guidance: {self._profile().guidance}\n\n"
            f"Analyzer summary:\n{analyzer_summary}\n\n"
            f"Plan:\n{plan}\n\n"
            "Implement tests or test-support changes only when possible. "
            "Do not change production behavior just to increase coverage. "
            "Run the coverage command or pytest after edits when useful.\n\n"
            f"Coverage command: {self.config.coverage_command}"
        )
        implementer = self.implementer_factory(
            self.provider,
            self.workspace,
            self.config.implementer_max_steps,
        )
        return await implementer.run(task)

    async def _review(
        self,
        report: CoverageReport,
        implementation: CodingAgentResult,
        plan: str,
    ) -> str:
        prompt = (
            f"Target line coverage: {self.config.target_line_coverage}%\n"
            f"Current line coverage after implementation: {report.line_coverage}%\n"
            f"Project profile: {self._profile().label}\n"
            f"Test framework: {self._test_framework()}\n"
            f"Coverage command passed: {report.passed}\n\n"
            f"Plan:\n{plan}\n\n"
            f"Implementer final answer:\n{implementation.final}\n\n"
            f"Coverage output:\n{self._trim(report.raw_output)}"
        )
        return await self.provider.generate(prompt, system_prompt=REVIEWER_PROMPT)

    def _result(
        self,
        report: CoverageReport,
        iterations: list[AgenticTestingIteration],
    ) -> AgenticTestingResult:
        return AgenticTestingResult(
            target_line_coverage=self.config.target_line_coverage,
            final_line_coverage=report.line_coverage,
            reached_target=report.line_coverage >= self.config.target_line_coverage,
            iterations=iterations,
            final_report=report,
        )

    def _trim(self, text: str, limit: int = 6000) -> str:
        if len(text) <= limit:
            return text
        return text[-limit:]

    def _profile(self):
        return get_project_profile(self.config.project_profile)

    def _test_framework(self) -> str:
        return self.config.test_framework or self._profile().test_framework
