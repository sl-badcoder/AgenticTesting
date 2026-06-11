import asyncio

from src.frontend.agents.FakeAgent import FakeAgent


def test_fake_agent_returns_configured_responses_and_records_calls() -> None:
    agent = FakeAgent(responses=["first", "second"])

    assert asyncio.run(agent.run("input-one")) == "first"
    assert asyncio.run(agent.run("input-two")) == "second"
    assert asyncio.run(agent.run("input-three")) == "second"
    assert agent.calls == ["input-one", "input-two", "input-three"]
