import asyncio
from dataclasses import dataclass, field
from typing import Any

from src.frontend.llm.base import LLMProvider, LLMProviderError


@dataclass(frozen=True)
class LlamaCppConfig:
    model_path: str
    n_ctx: int = 4096
    n_threads: int | None = None
    temperature: float = 0.2
    max_tokens: int = 512
    stop: list[str] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)


class LlamaCppProvider(LLMProvider):
    def __init__(self, config: LlamaCppConfig) -> None:
        self.config = config
        self._model: Any | None = None

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt, system_prompt)

    def _generate_sync(self, prompt: str, system_prompt: str | None = None) -> str:
        model = self._load_model()
        rendered_prompt = self._render_prompt(prompt, system_prompt)

        try:
            result = model(
                rendered_prompt,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                stop=self.config.stop or None,
            )
        except Exception as error:
            raise LLMProviderError("llama.cpp generation failed.") from error

        choices = result.get("choices", [])
        if not choices:
            return ""

        return str(choices[0].get("text", "")).strip()

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        try:
            from llama_cpp import Llama
        except ImportError as error:
            raise LLMProviderError(
                "llama.cpp support requires the 'llama-cpp-python' package."
            ) from error

        model_options = {
            "model_path": self.config.model_path,
            "n_ctx": self.config.n_ctx,
            "n_threads": self.config.n_threads,
            **self.config.options,
        }
        model_options = {
            key: value for key, value in model_options.items() if value is not None
        }
        self._model = Llama(**model_options)
        return self._model

    def _render_prompt(self, prompt: str, system_prompt: str | None) -> str:
        if not system_prompt:
            return prompt

        return f"System:\n{system_prompt}\n\nUser:\n{prompt}\n\nAssistant:\n"
