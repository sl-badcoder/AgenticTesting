import asyncio
from dataclasses import dataclass, field
from typing import Any

from src.frontend.llm.base import LLMProvider, LLMProviderError


@dataclass(frozen=True)
class HuggingFaceConfig:
    model_id: str
    device: str | int | None = None
    temperature: float = 0.2
    max_new_tokens: int = 512
    options: dict[str, Any] = field(default_factory=dict)
    generation_options: dict[str, Any] = field(default_factory=dict)


class HuggingFaceProvider(LLMProvider):
    def __init__(self, config: HuggingFaceConfig) -> None:
        self.config = config
        self._pipeline: Any | None = None

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return await asyncio.to_thread(self._generate_sync, prompt, system_prompt)

    def _generate_sync(self, prompt: str, system_prompt: str | None = None) -> str:
        pipeline = self._load_pipeline()
        rendered_prompt = self._render_prompt(prompt, system_prompt)

        try:
            result = pipeline(
                rendered_prompt,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                return_full_text=False,
                **self.config.generation_options,
            )
        except Exception as error:
            raise LLMProviderError("Hugging Face generation failed.") from error

        if not result:
            return ""

        return str(result[0].get("generated_text", "")).strip()

    def _load_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        try:
            from transformers import pipeline
        except ImportError as error:
            raise LLMProviderError(
                "Hugging Face support requires the 'transformers' package. "
                "Most local models also require 'torch' and 'accelerate'."
            ) from error

        pipeline_options = {
            "task": "text-generation",
            "model": self.config.model_id,
            "device": self.config.device,
            **self.config.options,
        }
        pipeline_options = {
            key: value for key, value in pipeline_options.items() if value is not None
        }
        self._pipeline = pipeline(**pipeline_options)
        return self._pipeline

    def _render_prompt(self, prompt: str, system_prompt: str | None) -> str:
        if not system_prompt:
            return prompt

        return f"System:\n{system_prompt}\n\nUser:\n{prompt}\n\nAssistant:\n"
