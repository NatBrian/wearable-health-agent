"""LLM client protocols, Prompt definition, and factory."""

from typing import Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

from wha.config import get_settings

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    """Token usage and latency tracking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


class Prompt(BaseModel):
    """Structured prompt with declared version and system/user messages."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prompt_id: str
    prompt_version: str = "1"
    system: str = ""
    user: str = ""
    schema_name: str | None = None


class LLMClient(Protocol):
    """Protocol implemented by all LLM providers."""

    def complete(
        self,
        prompt: Prompt,
        schema: type[T],
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> tuple[T, LLMUsage]:
        """Request structured completion matching schema from provider."""
        ...


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Return configured LLMClient instance (defaulting to cassette)."""
    selected_provider = provider or get_settings(reload=True).llm_provider
    if selected_provider == "cassette":
        from wha.llm.cassette import CassetteClient

        return CassetteClient()
    elif selected_provider == "ollama_native":
        from wha.llm.ollama import OllamaNativeClient

        return OllamaNativeClient()
    elif selected_provider == "openai_compatible":
        from wha.llm.openai_compat import OpenAICompatClient

        return OpenAICompatClient()

    # Fallback to cassette
    from wha.llm.cassette import CassetteClient

    return CassetteClient()
