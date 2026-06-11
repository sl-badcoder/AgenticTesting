from collections.abc import Iterable

from src.frontend.agents.Agent import BaseAgent


class FakeAgent(BaseAgent):
    def __init__(
        self,
        model: str = "fake-agent",
        instructions: str = "",
        name: str = "FakeAgent",
        responses: Iterable[str] | None = None,
    ) -> None:
        super().__init__(model=model, instructions=instructions, name=name)
        self.responses = list(responses or ["OK"])
        self.calls: list[str] = []

    async def run(self, input: str) -> str | None:
        self.calls.append(input)

        if len(self.calls) <= len(self.responses):
            return self.responses[len(self.calls) - 1]

        return self.responses[-1] if self.responses else None
