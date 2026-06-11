from dataclasses import dataclass

from src.frontend.llm.base import LLMProvider, LLMProviderError


@dataclass(frozen=True)
class OpenAIConfig:
    model: str = "gpt-4.1-mini"
    temperature: float = 0.2
    max_tokens: int = 1024
    api_key: str | None = None


class OpenAIProvider(LLMProvider):
    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config
        self._client = None

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        client = self._load_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
        except Exception as error:
            raise LLMProviderError("OpenAI generation failed.") from error

        return response.choices[0].message.content or ""

    def _load_client(self):
        if self._client is not None:
            return self._client

        try:
            from openai import AsyncOpenAI
        except ImportError as error:
            raise LLMProviderError(
                "OpenAI support requires the 'openai' package."
            ) from error

        self._client = AsyncOpenAI(api_key=self.config.api_key)
        return self._client
