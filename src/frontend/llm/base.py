from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Raised when a language model provider cannot generate a response."""


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text from a prompt."""
