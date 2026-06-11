import asyncio

from src.core.local_coding_agent import LocalCodingAgent
from src.core.workspace import RepositoryWorkspace
from src.frontend.llm.fake import FakeLLMProvider


def test_local_coding_agent_can_edit_file_with_fake_provider(tmp_path) -> None:
    target = tmp_path / "example.py"
    target.write_text("name = 'old'\n", encoding="utf-8")
    provider = FakeLLMProvider(
        responses=[
            '{"actions": [{"tool": "read_file", "path": "example.py"}], "final": null}',
            """{"actions": [{"tool": "replace_text", "path": "example.py", "old": "name = 'old'", "new": "name = 'new'"}], "final": null}""",
            '{"actions": [], "final": "Updated example.py."}',
        ]
    )
    workspace = RepositoryWorkspace(tmp_path)
    agent = LocalCodingAgent(provider, workspace, max_steps=3)

    result = asyncio.run(agent.run("Rename the value."))

    assert result.final == "Updated example.py."
    assert target.read_text(encoding="utf-8") == "name = 'new'\n"


def test_local_coding_agent_reports_invalid_json(tmp_path) -> None:
    provider = FakeLLMProvider(
        responses=[
            "not json",
            '{"actions": [], "final": "Recovered."}',
        ]
    )
    workspace = RepositoryWorkspace(tmp_path)
    agent = LocalCodingAgent(provider, workspace, max_steps=2)

    result = asyncio.run(agent.run("Do something."))

    assert result.final == "Recovered."
    assert "Invalid JSON response" in result.steps[0].observations[0]
