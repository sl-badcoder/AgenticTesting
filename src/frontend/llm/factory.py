from typing import Any

from src.frontend.llm.anthropic_provider import AnthropicConfig, AnthropicProvider
from src.frontend.llm.base import LLMProvider
from src.frontend.llm.fake import FakeLLMProvider
from src.frontend.llm.huggingface import HuggingFaceConfig, HuggingFaceProvider
from src.frontend.llm.llama_cpp import LlamaCppConfig, LlamaCppProvider
from src.frontend.llm.openai_provider import OpenAIConfig, OpenAIProvider


def create_llm_provider(config: dict[str, Any]) -> LLMProvider:
    provider_type = str(config.get("type", "")).lower()

    if provider_type in {"fake", "test"}:
        return FakeLLMProvider(responses=config.get("responses"))

    if provider_type in {"llama.cpp", "llama-cpp", "llamacpp"}:
        return LlamaCppProvider(
            LlamaCppConfig(
                model_path=config["model_path"],
                n_ctx=config.get("n_ctx", 4096),
                n_threads=config.get("n_threads"),
                temperature=config.get("temperature", 0.2),
                max_tokens=config.get("max_tokens", 512),
                stop=list(config.get("stop", [])),
                options=dict(config.get("options", {})),
            )
        )

    if provider_type in {"huggingface", "hf", "transformers"}:
        return HuggingFaceProvider(
            HuggingFaceConfig(
                model_id=config["model_id"],
                device=config.get("device"),
                temperature=config.get("temperature", 0.2),
                max_new_tokens=config.get("max_new_tokens", 512),
                options=dict(config.get("options", {})),
                generation_options=dict(config.get("generation_options", {})),
            )
        )

    if provider_type in {"openai", "chatgpt"}:
        return OpenAIProvider(
            OpenAIConfig(
                model=config.get("model", "gpt-4.1-mini"),
                temperature=config.get("temperature", 0.2),
                max_tokens=config.get("max_tokens", 1024),
                api_key=config.get("api_key"),
            )
        )

    if provider_type in {"anthropic", "claude"}:
        return AnthropicProvider(
            AnthropicConfig(
                model=config.get("model", "claude-3-5-haiku-latest"),
                temperature=config.get("temperature", 0.2),
                max_tokens=config.get("max_tokens", 1024),
                api_key=config.get("api_key"),
            )
        )

    raise ValueError(f"Unsupported LLM provider '{config.get('type')}'.")
