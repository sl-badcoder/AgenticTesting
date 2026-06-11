from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectProfile:
    key: str
    label: str
    test_framework: str
    coverage_command: str
    allowed_commands: tuple[str, ...]
    guidance: str


PROJECT_PROFILES: dict[str, ProjectProfile] = {
    "python-pytest": ProjectProfile(
        key="python-pytest",
        label="Python / pytest",
        test_framework="pytest",
        coverage_command="pytest --cov=. --cov-report=term-missing",
        allowed_commands=("pytest",),
        guidance=(
            "Create pytest tests. Prefer focused unit tests under tests/ or test/. "
            "Use fixtures and monkeypatching where useful."
        ),
    ),
    "dotnet": ProjectProfile(
        key="dotnet",
        label=".NET / xUnit, NUnit, or MSTest",
        test_framework="dotnet test",
        coverage_command="dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover",
        allowed_commands=("dotnet",),
        guidance=(
            "Create .NET unit tests that match the existing test project style. "
            "Prefer xUnit, NUnit, or MSTest based on packages already present."
        ),
    ),
    "cpp-gtest": ProjectProfile(
        key="cpp-gtest",
        label="C++ / GoogleTest",
        test_framework="GoogleTest",
        coverage_command="gcovr --txt",
        allowed_commands=("gcovr", "ctest"),
        guidance=(
            "Create C++ tests using GoogleTest conventions. Prefer TEST or TEST_F "
            "cases and place tests beside the existing test targets."
        ),
    ),
    "node-jest": ProjectProfile(
        key="node-jest",
        label="JavaScript or TypeScript / Jest",
        test_framework="Jest",
        coverage_command="npm test -- --coverage",
        allowed_commands=("npm",),
        guidance=(
            "Create Jest tests. Prefer existing test file naming and avoid changing "
            "runtime code unless testability requires a narrow seam."
        ),
    ),
    "custom": ProjectProfile(
        key="custom",
        label="Custom",
        test_framework="Custom",
        coverage_command="pytest --cov=. --cov-report=term-missing",
        allowed_commands=("pytest",),
        guidance=(
            "Follow the repository's existing test framework and style. Use the "
            "configured coverage command."
        ),
    ),
}


def get_project_profile(key: str) -> ProjectProfile:
    return PROJECT_PROFILES.get(key, PROJECT_PROFILES["custom"])
