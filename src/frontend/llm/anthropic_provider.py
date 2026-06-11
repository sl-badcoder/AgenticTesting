from dataclasses import dataclass

from src.frontend.llm.base import LLMProvider, LLMProviderError


@dataclass(frozen=True)
class AnthropicConfig:
    model: str = "claude-3-5-haiku-latest"
    temperature: float = 0.2
    max_tokens: int = 1024
    api_key: str | None = None


class AnthropicProvider(LLMProvider):
    def __init__(self, config: AnthropicConfig) -> None:
        self.config = config
        self._client = None

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        client = self._load_client()

        try:
            response = await client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt or "",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as error:
            raise LLMProviderError("Anthropic generation failed.") from error

        return "".join(
            block.text for block in response.content if getattr(block, "text", None)
        )

    def _load_client(self):
        if self._client is not None:
            return self._client

        try:
            from anthropic import AsyncAnthropic
        except ImportError as error:
            raise LLMProviderError(
                "Anthropic support requires the 'anthropic' package."
            ) from error

        self._client = AsyncAnthropic(api_key=self.config.api_key)
        return self._client
