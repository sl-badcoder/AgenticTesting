import json
from dataclasses import dataclass, field
from typing import Any

from src.core.workspace import CommandResult, RepositoryWorkspace, WorkspaceError
from src.frontend.llm.base import LLMProvider


SYSTEM_PROMPT = """You are a local coding agent working inside a repository.
You may inspect and edit files only by returning JSON tool actions.
Return exactly one JSON object with this shape:
{
  "actions": [
    {"tool": "list_files"},
    {"tool": "read_file", "path": "relative/path.py"},
    {"tool": "replace_text", "path": "relative/path.py", "old": "exact text", "new": "replacement text"},
    {"tool": "write_file", "path": "relative/path.py", "content": "full file content"},
    {"tool": "run_command", "command": "pytest --cov=. --cov-report=term-missing"}
  ],
  "final": null
}

When the task is complete, return:
{"actions": [], "final": "brief summary of what changed and how it was checked"}

Rules:
- Use relative paths only.
- Prefer read_file before editing existing files.
- Prefer replace_text for focused edits.
- Use run_command only for allowed test commands.
- Do not include markdown outside the JSON object.
"""


@dataclass(frozen=True)
class AgentStep:
    prompt: str
    response: str
    observations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CodingAgentResult:
    final: str | None
    steps: list[AgentStep]


class LocalCodingAgent:
    def __init__(
        self,
        provider: LLMProvider,
        workspace: RepositoryWorkspace,
        max_steps: int = 8,
    ) -> None:
        self.provider = provider
        self.workspace = workspace
        self.max_steps = max_steps

    async def run(self, task: str) -> CodingAgentResult:
        steps: list[AgentStep] = []
        observations = [
            f"Task: {task}",
            "No files have been inspected yet.",
        ]

        for _ in range(self.max_steps):
            prompt = self._build_prompt(observations)
            response = await self.provider.generate(prompt, system_prompt=SYSTEM_PROMPT)
            parsed = self._parse_response(response)
            step_observations: list[str]

            if isinstance(parsed, str):
                step_observations = [parsed]
                steps.append(AgentStep(prompt, response, step_observations))
                observations = step_observations
                continue

            final = parsed.get("final")
            actions = parsed.get("actions", [])
            if final and not actions:
                steps.append(AgentStep(prompt, response, [f"Final: {final}"]))
                return CodingAgentResult(final=str(final), steps=steps)

            step_observations = self._execute_actions(actions)
            steps.append(AgentStep(prompt, response, step_observations))
            observations = step_observations

        return CodingAgentResult(
            final=None,
            steps=steps,
        )

    def _build_prompt(self, observations: list[str]) -> str:
        observation_text = "\n".join(f"- {observation}" for observation in observations)
        return f"Previous observations:\n{observation_text}\n\nReturn the next JSON action object."

    def _parse_response(self, response: str) -> dict[str, Any] | str:
        response = self._extract_json(response)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as error:
            return f"Invalid JSON response: {error.msg}."

        if not isinstance(parsed, dict):
            return "Response must be a JSON object."

        if "actions" not in parsed or "final" not in parsed:
            return "Response must contain 'actions' and 'final'."

        if not isinstance(parsed["actions"], list):
            return "'actions' must be a list."

        return parsed

    def _extract_json(self, response: str) -> str:
        stripped = response.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return stripped[start : end + 1]

        return stripped

    def _execute_actions(self, actions: list[Any]) -> list[str]:
        if not actions:
            return ["No actions were requested."]

        observations: list[str] = []
        for action in actions:
            if not isinstance(action, dict):
                observations.append("Skipped invalid action because it is not an object.")
                continue

            try:
                observations.append(self._execute_action(action))
            except (KeyError, TypeError, WorkspaceError) as error:
                observations.append(f"Tool error: {error}")

        return observations

    def _execute_action(self, action: dict[str, Any]) -> str:
        tool = action.get("tool")

        if tool == "list_files":
            files = self.workspace.list_files()
            return "Files:\n" + "\n".join(files)

        if tool == "read_file":
            path = str(action["path"])
            content = self.workspace.read_file(path)
            return f"Read {path}:\n{content}"

        if tool == "replace_text":
            return self.workspace.replace_text(
                relative_path=str(action["path"]),
                old=str(action["old"]),
                new=str(action["new"]),
            )

        if tool == "write_file":
            return self.workspace.write_file(
                relative_path=str(action["path"]),
                content=str(action["content"]),
            )

        if tool == "run_command":
            result = self.workspace.run_command(str(action["command"]))
            return self._format_command_result(result)

        raise WorkspaceError(f"Unsupported tool '{tool}'.")

    def _format_command_result(self, result: CommandResult) -> str:
        output = [
            f"Command: {result.command}",
            f"Exit code: {result.exit_code}",
        ]
        if result.stdout:
            output.append(f"stdout:\n{result.stdout}")
        if result.stderr:
            output.append(f"stderr:\n{result.stderr}")
        return "\n".join(output)
