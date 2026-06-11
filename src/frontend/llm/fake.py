from collections.abc import Iterable

from src.frontend.llm.base import LLMProvider


class FakeLLMProvider(LLMProvider):
    def __init__(self, responses: Iterable[str] | None = None) -> None:
        self.responses = list(responses or ["OK"])
        self.prompts: list[tuple[str, str | None]] = []

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        self.prompts.append((prompt, system_prompt))

        if len(self.prompts) <= len(self.responses):
            return self.responses[len(self.prompts) - 1]

        return self.responses[-1] if self.responses else ""
