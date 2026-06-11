import pytest

from src.frontend.llm import (
    AnthropicProvider,
    FakeLLMProvider,
    HuggingFaceProvider,
    LlamaCppProvider,
    OpenAIProvider,
    create_llm_provider,
)


def test_create_llm_provider_returns_fake_provider() -> None:
    provider = create_llm_provider({"type": "fake", "responses": ["done"]})

    assert isinstance(provider, FakeLLMProvider)


def test_create_llm_provider_returns_llama_cpp_provider() -> None:
    provider = create_llm_provider(
        {
            "type": "llama.cpp",
            "model_path": "models/example.gguf",
        }
    )

    assert isinstance(provider, LlamaCppProvider)


def test_create_llm_provider_returns_huggingface_provider() -> None:
    provider = create_llm_provider(
        {
            "type": "huggingface",
            "model_id": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        }
    )

    assert isinstance(provider, HuggingFaceProvider)


def test_create_llm_provider_returns_openai_provider() -> None:
    provider = create_llm_provider({"type": "openai", "model": "gpt-test"})

    assert isinstance(provider, OpenAIProvider)


def test_create_llm_provider_returns_anthropic_provider() -> None:
    provider = create_llm_provider({"type": "anthropic", "model": "claude-test"})

    assert isinstance(provider, AnthropicProvider)


def test_create_llm_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        create_llm_provider({"type": "unknown"})
